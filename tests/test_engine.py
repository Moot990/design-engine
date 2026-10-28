import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from PIL import Image
from pypdf import PdfReader

from engine.affiliate import AI_NOTICE, DISCLOSURE, affiliate_link, validate_affiliate_url
from engine.common import ROOT, EngineError, config, request, write_csv
from engine.ideas import candidates, ledger_row
from engine.media import caption_frame
from engine.pipeline import record_publication, short_copy, run as run_pipeline
from engine.products import product_pack
from engine.providers import fingerprint, fixture_image, is_duplicate, pin_text, image_account_ready
from engine.publish import pinterest, pinterest_bearer, youtube


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.settings = config()

    def tearDown(self):
        self.temp.cleanup()

    def test_ideas_never_repeat_and_daily_items_differ(self):
        prior = []
        seen = set()
        for day in range(1, 29):
            batch = candidates(self.settings, f"2026-10-{day:02}", prior)
            self.assertEqual(len({i["item"]["id"] for i in batch}), 4)
            self.assertEqual(len({i["style"]["id"] for i in batch}), 4)
            for idea in batch:
                self.assertNotIn(idea["id"], seen)
                seen.add(idea["id"])
                prior.append(ledger_row(idea, f"2026-10-{day:02}", "reserved"))

    def test_product_links_sa_tag_and_stale_product_fallback(self):
        idea = candidates(self.settings, "2026-10-29", [])[0]
        path = self.directory / "products.csv"
        fields = ["item_id", "style_id", "asin", "search_query", "label_en", "label_ar", "active", "reviewed_on"]
        row = dict.fromkeys(fields, "")
        row.update(item_id=idea["item"]["id"], asin="B012345678", active="true", reviewed_on="2026-10-29")
        write_csv(path, [row], fields)
        link = affiliate_link(idea, "test-21", path, date(2026, 10, 29))
        self.assertIn("/dp/B012345678?tag=test-21", link)
        self.assertTrue(validate_affiliate_url(link))
        self.assertIn("/s?", affiliate_link(idea, "test-21", path, date(2026, 11, 20)))
        self.assertFalse(validate_affiliate_url("https://www.amazon.sa.attacker.test/?tag=test-21"))
        with self.assertRaises(EngineError):
            affiliate_link(idea, "wrong-20", path)

    def test_csv_formula_injection_is_neutralized(self):
        path = self.directory / "export.csv"
        write_csv(path, [{"title": "=HYPERLINK(1)"}], ["title"])
        self.assertIn("'=HYPERLINK", path.read_text(encoding="utf-8-sig"))

    def test_duplicate_image_rejected_even_when_reencoded(self):
        first, second = self.directory / "one.jpg", self.directory / "two.jpg"
        fixture_image(first, 1)
        with Image.open(first) as original:
            original.save(second, quality=72)
        hash_ = fingerprint(first)
        self.assertTrue(is_duplicate(fingerprint(second), {hash_: {}}))
        flat = self.directory / "flat.jpg"
        Image.new("RGB", (1000, 1500), "white").save(flat)
        with self.assertRaises(EngineError):
            fingerprint(flat)

    def test_no_retry_after_ambiguous_publish_and_no_secret_leak(self):
        with patch("engine.common.requests.request", side_effect=requests.ConnectionError("sensitive-token")) as call:
            with self.assertRaises(EngineError) as raised:
                request("POST", "https://example.test", service="publish", json={})
            self.assertEqual(call.call_count, 1)
            self.assertNotIn("sensitive-token", str(raised.exception))

    def test_safe_read_retries_transient_failure(self):
        bad, good = Mock(status_code=503, headers={}), Mock(status_code=200)
        with patch("engine.common.requests.request", side_effect=[bad, good]) as call, patch("engine.common.time.sleep"):
            self.assertIs(request("GET", "https://example.test", service="test", retry_safe=True), good)
            self.assertEqual(call.call_count, 2)

    def test_image_alias_and_earned_only_credit_bound(self):
        model = {"name": "tongyi-mai/z-image-turbo", "aliases": ["zimage"], "paid_only": False, "community": False, "category": "image", "flat_rate": True, "pricing": {"currency": "pollen", "completionImageTokens": "0.004"}}
        def reply(value):
            result = Mock()
            result.json.return_value = value
            return result
        with patch.dict("os.environ", {"POLLINATIONS_QUEST_ONLY": "true", "POLLINATIONS_API_KEY": "test-key"}):
            with patch("engine.providers.request", side_effect=[reply({"balance": 1, "accountBalance": {"tier": 1, "paid": 0}}), reply([model])]):
                self.assertEqual(image_account_ready(self.settings)["Authorization"], "Bearer test-key")
            with patch("engine.providers.request", side_effect=[reply({"balance": .001, "accountBalance": {"tier": .001, "paid": 0}}), reply([model])]):
                with self.assertRaises(EngineError):
                    image_account_ready(self.settings)
            with patch("engine.providers.request", return_value=reply({"balance": 10, "accountBalance": {"tier": 5, "paid": 5}})):
                with self.assertRaises(EngineError):
                    image_account_ready(self.settings)

    def test_outbox_persists_before_network_and_blocks_second_attempt(self):
        state = self.directory / "history.json"
        history = {"publications": {}}
        def failure():
            self.assertEqual(json.loads(state.read_text())["publications"]["item"]["status"], "inflight")
            raise EngineError("Ambiguous upload result")
        with patch("engine.pipeline.checkpoint") as checkpoint:
            with self.assertRaises(EngineError):
                record_publication(history, state, "2026-10-29", "item", "pinterest", failure)
            self.assertGreaterEqual(checkpoint.call_count, 2)
            callback = Mock()
            record_publication(history, state, "2026-10-29", "item", "pinterest", callback)
            callback.assert_not_called()
            self.assertEqual(history["publications"]["item"]["status"], "unknown")

    def test_failed_checkpoint_prevents_remote_publish(self):
        callback = Mock()
        with patch("engine.pipeline.checkpoint", side_effect=EngineError("push failed")):
            with self.assertRaises(EngineError):
                record_publication({"publications": {}}, self.directory / "history.json", "2026-10-29", "item", "youtube", callback)
        callback.assert_not_called()

    def test_bilingual_text_disclosure_and_caption_render(self):
        idea = candidates(self.settings, "2026-10-29", [])[0]
        copy = pin_text(self.settings, idea, fixture=True)
        self.assertIn(DISCLOSURE, copy["description"])
        self.assertIn(AI_NOTICE, copy["description"])
        self.assertLess(len(copy["title"]), 100)
        source = self.directory / "source.jpg"
        fixture_image(source, 2)
        target = ROOT / "output" / "qa"
        target.mkdir(parents=True, exist_ok=True)
        for language, title, lesson in (("ar", "غرفة معيشة هادئة", "توازن الخامات والإضاءة"), ("en", "A calmer living room", "Balance texture and lighting")):
            output = target / f"caption-{language}.png"
            caption_frame(source, title, lesson, language, output)
            with Image.open(output) as rendered:
                self.assertEqual(rendered.size, (720, 1280))

    def test_product_pack_and_fixture_sale_guard(self):
        image = self.directory / "source.jpg"
        fixture_image(image, 0)
        entry = {"path": str(image), "style": "Warm minimal", "palette_name": "Sand and olive", "colors": ["#E2D5BF", "#737A55", "#403C34"], "fixture": True}
        paths = product_pack([entry], self.directory / "pack", fixture=True)
        for path in paths:
            self.assertEqual(len(PdfReader(path).pages), 1)
        with self.assertRaises(EngineError):
            product_pack([entry], self.directory / "real-pack")

    def test_pinterest_payload_uses_base64_and_disclosure(self):
        image = self.directory / "pin.jpg"
        fixture_image(image, 0)
        reply = Mock()
        reply.json.return_value = {"id": "12345"}
        with patch("engine.publish.request", return_value=reply) as call, patch("engine.publish.pinterest_bearer", return_value="test-only"):
            self.assertEqual(pinterest(image, "A useful room idea", DISCLOSURE, "https://www.amazon.sa/s?k=lamp&tag=test-21", "1234"), "12345")
            payload = call.call_args.kwargs["json"]
            self.assertEqual(payload["media_source"]["source_type"], "image_base64")
            self.assertIn("#ad", payload["description"])
            self.assertNotIn("retry_safe", call.call_args.kwargs)

    def test_youtube_payload_sets_ai_disclosure_and_private(self):
        video = self.directory / "test.mp4"
        video.write_bytes(b"test-fixture")
        token = Mock()
        token.json.return_value = {"access_token": "ephemeral-test-token"}
        start = Mock(headers={"Location": "https://www.googleapis.com/upload/session-test"})
        finish = Mock()
        finish.json.return_value = {"id": "video123", "status": {"privacyStatus": "private"}}
        with patch("engine.publish.request", side_effect=[token, start, finish]) as call, patch("engine.publish.secret", return_value="test-only"):
            self.assertEqual(youtube(video, "Example", DISCLOSURE), ("video123", "private"))
            status = call.call_args_list[1].kwargs["json"]["status"]
            self.assertTrue(status["containsSyntheticMedia"])
            self.assertEqual(status["privacyStatus"], "private")
            self.assertNotIn("retry_safe", call.call_args_list[2].kwargs)

    def test_pinterest_rotation_persists_before_using_new_token(self):
        pinterest_bearer.cache_clear()
        response = Mock()
        response.json.return_value = {"access_token": "new-test-access", "refresh_token": "rotated-test-refresh"}
        with patch.dict("os.environ", {"PINTEREST_REFRESH_TOKEN": "old-test-refresh"}), patch("engine.publish.secret", return_value="test-only"), patch("engine.publish.request", return_value=response), patch("engine.publish.save_refresh_secret") as save:
            self.assertEqual(pinterest_bearer(), "new-test-access")
            save.assert_called_once_with("PINTEREST_REFRESH_TOKEN", "rotated-test-refresh")
        pinterest_bearer.cache_clear()

    def test_full_publishing_control_flow_exports_confirmed_ids_and_blocks_rerun(self):
        state = self.directory / "state"
        state.mkdir()
        (state / "ideas.csv").write_text((ROOT / "state/ideas.csv").read_text(encoding="utf-8-sig"), encoding="utf-8")
        (state / "history.json").write_text('{"images":{},"publications":{},"runs":{}}')
        products = self.directory / "data"
        products.mkdir()
        (products / "products.csv").write_text((ROOT / "data/products.csv").read_text(encoding="utf-8-sig"), encoding="utf-8")
        count = [0]
        def image(settings, prompt, seed, destination):
            fixture_image(destination, count[0])
            count[0] += 1
        def render(images, copy, settings, language, directory, **kwargs):
            Path(directory).mkdir(parents=True)
            output = Path(directory) / "short.mp4"
            output.write_bytes(b"test")
            return output, []
        copy = {"title": "A practical room idea", "description": DISCLOSURE, "script": "A practical design lesson."}
        short = {"hook": "Four useful room details", "script": "A useful design lesson", "captions": ["one", "two", "three", "four"]}
        environment = {"GEMINI_API_KEY": "test", "POLLINATIONS_API_KEY": "test", "AMAZON_ASSOCIATE_TAG": "test-21", "GEMINI_FREE_TIER_CONFIRMED": "true", "POLLINATIONS_QUEST_ONLY": "true", "PINTEREST_PUBLISH": "true", "YOUTUBE_PUBLISH": "true", "PINTEREST_ACCESS_TOKEN": "test", "PINTEREST_BOARD_ID": "123", "PINTEREST_REFRESH_TOKEN": "", "YOUTUBE_CLIENT_ID": "test", "YOUTUBE_CLIENT_SECRET": "test", "YOUTUBE_REFRESH_TOKEN": "test", "PUBLISHING_REVIEWED": "true", "ACTIONS_PRODUCTION_APPROVED": "true"}
        with patch.dict("os.environ", environment), patch("engine.pipeline.ROOT", self.directory), patch("engine.pipeline.checkpoint"), patch("engine.pipeline.generate_image", side_effect=image), patch("engine.pipeline.vision_review", return_value=True), patch("engine.pipeline.is_duplicate", return_value=False), patch("engine.pipeline.pin_text", return_value=copy), patch("engine.pipeline.short_copy", return_value=short), patch("engine.pipeline.render_short", side_effect=render), patch("engine.pipeline.publish.pinterest", return_value="pin123") as pin, patch("engine.pipeline.publish.youtube", return_value=("video123", "private")) as video:
            output = self.directory / "output"
            run_pipeline(self.settings, "publish", "2026-10-29", output, state)
            self.assertEqual(pin.call_count, 4)
            self.assertEqual(video.call_count, 1)
            self.assertIn("published,pin123", (output / "pinterest-upload-manifest.csv").read_text(encoding="utf-8-sig"))
            self.assertIn("video123", (output / "youtube-upload-manifest.csv").read_text(encoding="utf-8-sig"))
            self.assertEqual(len(json.loads((state / "history.json").read_text())["publications"]), 5)
            with self.assertRaises(EngineError):
                run_pipeline(self.settings, "publish", "2026-10-29", output, state)
            self.assertEqual(pin.call_count, 4)
if __name__ == "__main__":
    unittest.main(verbosity=2)

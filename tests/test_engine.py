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

    def test_egypt_product_url_retags_and_stale_product_falls_back(self):
        idea = candidates(self.settings, "2026-10-29", [])[0]
        path = self.directory / "products.csv"
        fields = ["item_id", "style_id", "product_url", "asin", "search_query", "label_en", "label_ar", "active", "reviewed_on"]
        row = dict.fromkeys(fields, "")
        row.update(item_id=idea["item"]["id"], product_url="https://amazon.eg/gp/product/B012345678?tag=old-id&ref=old", active="true", reviewed_on="2026-10-29")
        write_csv(path, [row], fields)
        link = affiliate_link(idea, "egypt-account-id", path, date(2026, 10, 29))
        self.assertEqual(link, "https://www.amazon.eg/dp/B012345678?tag=egypt-account-id")
        self.assertTrue(validate_affiliate_url(link))
        self.assertIn("https://www.amazon.eg/s?", affiliate_link(idea, "egypt-account-id", path, date(2026, 11, 20)))
        row["product_url"] = "https://www.amazon.com/dp/B012345678"
        write_csv(path, [row], fields)
        with self.assertRaises(EngineError):
            affiliate_link(idea, "egypt-account-id", path, date(2026, 10, 29))
        with self.assertRaises(EngineError):
            affiliate_link(idea, "invalid&tag", path)

    def test_affiliate_market_override_and_url_safety(self):
        from engine.affiliate import affiliate_program
        with patch.dict("os.environ", {"AFFILIATE_PROGRAM": "amazon.com"}):
            self.assertEqual(affiliate_program("amazon.eg"), "amazon.com")
            self.assertTrue(validate_affiliate_url("https://www.amazon.com/dp/B012345678?tag=test-id"))
            self.assertFalse(validate_affiliate_url("https://www.amazon.eg/dp/B012345678?tag=test-id"))
        with patch.dict("os.environ", {"AFFILIATE_PROGRAM": ""}):
            self.assertEqual(affiliate_program(self.settings["AFFILIATE_PROGRAM"]), "amazon.eg")
            for url in ["https://www.amazon.eg.attacker.test/s?k=lamp&tag=id", "https://user@www.amazon.eg/s?k=lamp&tag=id", "https://www.amazon.eg:bad/s?k=lamp&tag=id", "https://www.amazon.eg/s?k=lamp&tag=a&tag=b", "http://www.amazon.eg/s?k=lamp&tag=id"]:
                self.assertFalse(validate_affiliate_url(url), url)
        with patch.dict("os.environ", {"AFFILIATE_PROGRAM": "attacker.test"}):
            with self.assertRaises(EngineError):
                affiliate_program()

    def test_arabic_first_mix_and_fixture_narration(self):
        batch = candidates(self.settings, "2026-10-29", [])
        self.assertEqual([idea["language"] for idea in batch], ["ar", "ar", "ar", "en"])
        self.assertEqual(self.settings["primary_language"], "ar")
        self.assertEqual(self.settings["timezone"], "Africa/Cairo")
        copy = pin_text(self.settings, batch[0], fixture=True)
        self.assertIn("اختبار", copy["title"])
        self.assertIn(DISCLOSURE, copy["description"])
        short = short_copy(self.settings, [{"idea": idea} for idea in batch], "ar", fixture=True)
        self.assertIn("راجع", short["script"])

    def test_large_image_seed_uses_signed_integer_range(self):
        from engine.providers import generate_image
        source = self.directory / "source.jpg"
        fixture_image(source, 0)
        response = Mock(headers={"Content-Type": "image/jpeg"}, content=source.read_bytes())
        with patch("engine.providers.image_account_ready", return_value={}), patch("engine.providers.request", return_value=response) as call:
            generate_image(self.settings, "A room", 0xFC83DDEC, self.directory / "result.jpg")
        seed = call.call_args.kwargs["params"]["seed"]
        self.assertEqual(seed, 0x7C83DDEC)
        self.assertGreaterEqual(seed, 0)
        self.assertLessEqual(seed, 2147483647)

    def test_optional_hashtags_are_normalized_without_discarding_arabic_copy(self):
        idea = candidates(self.settings, "2026-10-29", [])[0]
        value = {"title": "غرفة معيشة بسيطة", "description": "اختار خامات مناسبة لمساحة الغرفة.", "script": " ".join(["اختار خامات مناسبة"] * 10), "hashtags": ["ديكور", " #غرفة_المعيشة ", "https://bad.test", 4]}
        with patch("engine.providers.gemini", return_value=value.copy()):
            copy = pin_text(self.settings, idea)
        self.assertIn("#ديكور #غرفة_المعيشة", copy["description"])
        self.assertNotIn("bad.test", copy["description"])
        with patch("engine.providers.gemini", return_value={**value, "title": "English title"}):
            with self.assertRaises(EngineError):
                pin_text(self.settings, idea)

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
            self.assertEqual(pinterest(image, "A useful room idea", DISCLOSURE, "https://www.amazon.eg/s?k=lamp&tag=test-eg", "1234"), "12345")
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

    def test_retry_empty_preserves_failed_history_and_rejected_ideas(self):
        state = self.directory / "state"
        state.mkdir()
        idea = candidates(self.settings, "2026-10-30", [])[0]
        write_csv(state / "ideas.csv", [ledger_row(idea, "2026-10-30", "rejected")], ["idea_id", "date", "room", "style", "palette", "item", "format", "language", "status"])
        old = {"status": "needs-review", "accepted": 0, "pins_exported": 0, "video_ready": False, "warnings": ["provider rejected request"]}
        history = {"images": {}, "publications": {}, "runs": {"2026-10-30": old}}
        (state / "history.json").write_text(json.dumps(history))
        with patch("engine.pipeline.readiness", return_value=[]), patch("engine.pipeline.checkpoint"), patch("engine.pipeline.generate_image", side_effect=EngineError("test rejection")):
            with self.assertRaises(EngineError):
                run_pipeline(self.settings, "generate", "2026-10-30", self.directory / "new", state, retry_empty=True)
        saved = json.loads((state / "history.json").read_text())
        self.assertEqual(saved["runs"]["2026-10-30"]["previous_attempts"], [old])
        from engine.common import read_csv
        self.assertEqual(len(read_csv(state / "ideas.csv")), 5)
        self.assertEqual(read_csv(state / "ideas.csv")[0]["idea_id"], idea["id"])
        history["publications"]["unknown"] = {"date": "2026-10-30", "status": "unknown"}
        (state / "history.json").write_text(json.dumps(history))
        with patch("engine.pipeline.readiness", return_value=[]), patch("engine.pipeline.generate_image") as image:
            with self.assertRaises(EngineError):
                run_pipeline(self.settings, "generate", "2026-10-30", self.directory / "blocked", state, retry_empty=True)
        image.assert_not_called()

    def test_resume_reuses_two_accepted_images_and_generates_only_two_more(self):
        from engine.pipeline import IDEA_FIELDS, PIN_FIELDS
        from engine.common import read_csv
        state, batch, output = [self.directory / name for name in ("state", "partial", "completed")]
        state.mkdir()
        archive = batch / "image-archive"
        archive.mkdir(parents=True)
        day = "2026-10-27"
        choices = candidates(self.settings, day, [])
        ideas = [choices[0], choices[3]]
        pins, hashes = [], {}
        for n, idea in enumerate(ideas):
            image = archive / (idea["id"] + ".jpg")
            fixture_image(image, n)
            image.with_suffix(".json").write_text(json.dumps({"id": idea["id"], "fixture": False, "vision_approved": True}))
            hashes[fingerprint(image)] = {"id": idea["id"], "date": day}
            pins.append({"idea_id": idea["id"], "image_file": "image-archive/" + image.name, "title": "old", "description": "old", "link": "https://www.amazon.eg/s?k=lamp&tag=test-eg", "language": idea["language"], "status": "ready-for-manual-upload"})
        write_csv(batch / "pinterest-upload-manifest.csv", pins, PIN_FIELDS)
        (batch / "readiness.json").write_text(json.dumps({"mode": "generate", "date": day, "fixture": False}))
        write_csv(state / "ideas.csv", [ledger_row(idea, day, "accepted") for idea in ideas], IDEA_FIELDS)
        old = {"status": "needs-review", "accepted": 2, "pins_exported": 2, "video_ready": False, "warnings": ["malformed copy"]}
        history = {"images": hashes, "publications": {}, "runs": {day: old}}
        (state / "history.json").write_text(json.dumps(history))
        counter = [2]
        def image(settings, prompt, seed, destination):
            fixture_image(destination, counter[0])
            counter[0] += 1
        def render(images, copy, settings, language, directory, **kwargs):
            self.assertEqual(len(images), 4)
            directory.mkdir(parents=True)
            path = directory / "short.mp4"
            path.write_bytes(b"mock render")
            return path, []
        copy = {"title": "نص مراجع", "description": DISCLOSURE, "script": "نص مراجع"}
        short = {"hook": "تفاصيل للمعيشة", "script": "نص مراجع", "captions": ["one", "two", "three", "four"]}
        with patch.dict("os.environ", {"AMAZON_ASSOCIATE_TAG": "test-eg"}), patch("engine.pipeline.readiness", return_value=[]), patch("engine.pipeline.checkpoint"), patch("engine.pipeline.generate_image", side_effect=image) as generate, patch("engine.pipeline.vision_review", return_value=True), patch("engine.pipeline.is_duplicate", return_value=False), patch("engine.pipeline.pin_text", return_value=copy), patch("engine.recovery.pin_text", return_value=copy), patch("engine.pipeline.short_copy", return_value=short), patch("engine.pipeline.render_short", side_effect=render):
            run_pipeline(self.settings, "generate", day, output, state, resume_batch=batch)
        self.assertEqual(generate.call_count, 2)
        completed = read_csv(output / "pinterest-upload-manifest.csv")
        self.assertEqual(len(completed), 4)
        self.assertEqual([p["language"] for p in completed].count("ar"), 3)
        self.assertEqual([p["language"] for p in completed].count("en"), 1)
        saved = json.loads((state / "history.json").read_text())
        self.assertEqual(saved["runs"][day]["previous_attempts"], [old])
        self.assertEqual(len(saved["images"]), 4)
        self.assertEqual(saved["publications"], {})
        history["publications"]["unknown"] = {"date": day, "status": "unknown"}
        (state / "history.json").write_text(json.dumps(history))
        with patch("engine.pipeline.readiness", return_value=[]), patch("engine.recovery.restore_batch") as restore:
            with self.assertRaises(EngineError):
                run_pipeline(self.settings, "generate", day, self.directory / "blocked", state, resume_batch=batch)
        restore.assert_not_called()

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
        environment = {"GEMINI_API_KEY": "test", "POLLINATIONS_API_KEY": "test", "AMAZON_ASSOCIATE_TAG": "test-eg", "GEMINI_FREE_TIER_CONFIRMED": "true", "POLLINATIONS_QUEST_ONLY": "true", "PINTEREST_PUBLISH": "true", "YOUTUBE_PUBLISH": "true", "PINTEREST_ACCESS_TOKEN": "test", "PINTEREST_BOARD_ID": "123", "PINTEREST_REFRESH_TOKEN": "", "YOUTUBE_CLIENT_ID": "test", "YOUTUBE_CLIENT_SECRET": "test", "YOUTUBE_REFRESH_TOKEN": "test", "PUBLISHING_REVIEWED": "true", "ACTIONS_PRODUCTION_APPROVED": "true"}
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

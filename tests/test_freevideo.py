import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from engine.common import ROOT, EngineError, config
from engine.freevideo import Client, PREFIX, animate_selected
from engine.media import media_executable, probe, render_short, run_media
from engine.providers import fixture_image


class FreeVideoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.settings = config()
        self.settings["video_backend"] = "freevideo"
        self.settings["freevideo"] = {**self.settings["freevideo"], "max_ai_clips_per_week": 1, "cooldown_seconds": 0}
        self.image = self.directory / "first.jpg"
        fixture_image(self.image, 0)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_backend_does_not_contact_local_app(self):
        self.settings["video_backend"] = "ffmpeg"
        with patch("engine.freevideo.Client") as client:
            self.assertEqual(animate_selected([self.image], self.settings, self.directory), ({}, []))
            client.assert_not_called()

    def test_hosted_and_uncleared_publishing_fall_back_before_authentication(self):
        for env, publishing in (({"GITHUB_ACTIONS": "true"}, False), ({"GITHUB_ACTIONS": ""}, True)):
            with patch.dict("os.environ", env), patch("engine.freevideo.Client") as client:
                clips, warnings = animate_selected([self.image], self.settings, self.directory, publishing=publishing)
                self.assertFalse(clips)
                self.assertTrue(warnings)
                client.assert_not_called()

    def test_agent_credentials_cannot_go_to_remote_or_redirected_origin(self):
        for origin in ("http://example.com:8188", "http://127.0.0.1:8188/other", "http://user:secret@127.0.0.1:8188"):
            with patch.dict("os.environ", {"FREEVIDEO_URL": origin, "FREEVIDEO_AGENT_TOKEN": "test-only"}):
                with self.assertRaises(EngineError):
                    Client(time.monotonic() + 10)
        with patch.dict("os.environ", {"FREEVIDEO_URL": "http://127.0.0.1:8188", "FREEVIDEO_AGENT_TOKEN": "test-only"}):
            client = Client(time.monotonic() - 1)
            with patch.object(client.session, "request") as send:
                with self.assertRaises(EngineError):
                    client.call("GET", PREFIX)
                send.assert_not_called()
            client.session.close()

    def test_thermal_limit_prevents_job_submission(self):
        client = Mock()
        client.call.return_value = {"ready": True, "features": {"generate.first_frame": True}, "queue": {}}
        with patch.dict("os.environ", {"GITHUB_ACTIONS": ""}), patch("engine.freevideo.Client", return_value=client), patch("engine.freevideo.gpu_sample", return_value={"temperature_c": 85}):
            clips, warnings = animate_selected([self.image], self.settings, self.directory / "render", budget_path=self.directory / "budget.json")
        self.assertFalse(clips)
        self.assertIn("temperature", warnings[0])
        self.assertEqual(client.call.call_count, 1)  # Readiness only, no generation.

    def test_attempt_quota_and_cancellation_survive_failure(self):
        client = Mock()
        client.cancel.return_value = True
        def call(method, path, body=None, **kwargs):
            if path == PREFIX:
                return {"ready": True, "features": {"generate.first_frame": True}, "queue": {}}
            if path.endswith("/media"):
                return {"file": "uploaded/first.jpg"}
            if path.endswith("/plan"):
                return {}
            if path.endswith("/jobs"):
                return {"job": {"id": "j123456789abc", "status": "running"}}
            raise EngineError("test polling failure")
        client.call.side_effect = call
        budget = self.directory / "budget.json"
        with patch.dict("os.environ", {"GITHUB_ACTIONS": ""}), patch("engine.freevideo.Client", return_value=client), patch("engine.freevideo.gpu_sample", return_value=None):
            clips, warnings = animate_selected([self.image], self.settings, self.directory / "run1", budget_path=budget)
            self.assertFalse(clips)
            client.cancel.assert_called_once_with("j123456789abc")
            data = json.loads(budget.read_text())
            self.assertEqual(sum(data["weeks"].values()), 1)
            clips, warnings = animate_selected([self.image], self.settings, self.directory / "run2", budget_path=budget)
            self.assertIn("allowance exhausted", warnings[0])
            self.assertEqual(len(json.loads(budget.read_text())["attempts"]), 1)
        self.assertFalse(budget.with_suffix(".lock").exists())

    def test_motion_clip_really_assembles_with_caption_overlay(self):
        source = self.directory / "motion.mp4"
        run_media(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=544x960:rate=24", "-t", "5", "-an", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(source)])
        images = []
        for number in range(4):
            image = self.directory / f"image{number}.jpg"
            fixture_image(image, number)
            images.append(image)
        copy = {"hook": "TEST - motion plus stills", "captions": ["One useful lesson"] * 4, "script": "A test of mixed video assembly."}
        async def no_voice(*args):
            raise EngineError("Test captions-only voice fallback")
        output = ROOT / "output/mixed-backend-test"
        with patch("engine.freevideo.animate_selected", return_value=({0: source}, [])), patch("engine.media._voice", side_effect=no_voice):
            video, warnings = render_short(images, copy, self.settings, "en", output)
        self.assertEqual(round(float(probe(video)["format"]["duration"])), 24)
        self.assertTrue(video.is_file())
        self.assertFalse(any("assembly failed" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main(verbosity=2)

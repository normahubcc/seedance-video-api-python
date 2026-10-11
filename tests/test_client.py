"""
Unit tests for NormaHub SeeDance Video SDK (Sync and Async clients).
"""

import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from seedance.cli import main as cli_main
from seedance.client import AsyncNormaVideoClient, NormaVideoClient, encode_image_to_data_uri
from seedance.exceptions import (
    AuthenticationError,
    BudgetExceededError,
    ModelNotAllowedError,
    NormaVideoError,
    VideoGenerationFailedError,
)
from seedance.types import TaskStatus, VideoModel, VideoTask


class TestNormaVideoClient(unittest.TestCase):
    def test_missing_api_key_raises_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(AuthenticationError):
                NormaVideoClient(api_key="")

    def test_client_init_with_key(self):
        client = NormaVideoClient(api_key="nr_hub_test_12345")
        self.assertEqual(client.api_key, "nr_hub_test_12345")
        self.assertEqual(client.base_url, "https://api.normahub.cc/v1")
        self.assertEqual(client.max_retries, 3)

    def test_task_status_properties(self):
        task_pending = VideoTask(
            id="t1",
            model="seedance-2.5",
            prompt="test",
            status=TaskStatus.PROCESSING,
            created_at=12345,
        )
        self.assertFalse(task_pending.is_finished)
        self.assertFalse(task_pending.is_successful)

        task_completed = VideoTask(
            id="t2",
            model="seedance-2.5",
            prompt="test",
            status=TaskStatus.COMPLETED,
            created_at=12345,
            video_url="https://api.normahub.cc/videos/t2.mp4",
        )
        self.assertTrue(task_completed.is_finished)
        self.assertTrue(task_completed.is_successful)

    def test_video_model_enum_values(self):
        self.assertEqual(VideoModel.SEEDANCE_2_5.value, "seedance-2.5")
        self.assertEqual(VideoModel.GROK_IMAGINE_VIDEO_1_5.value, "grok-imagine-video-1.5")

    @patch("urllib.request.urlopen")
    def test_create_task_text(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "id": "task_abc_123",
            "status": "pending",
            "created_at": 1700000000,
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        client = NormaVideoClient(api_key="nr_hub_test")
        task = client.create_task(
            prompt="Futuristic city",
            model=VideoModel.SEEDANCE_2_5,
            duration=5,
        )

        self.assertEqual(task.id, "task_abc_123")
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(task.prompt, "Futuristic city")

    @patch("urllib.request.urlopen")
    def test_create_task_with_image_path(self, mock_urlopen):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tf.write(b"\x89PNG\r\n\x1a\nfake_image_bytes")
            tf_path = Path(tf.name)

        try:
            captured_requests = []

            def fake_urlopen(req, timeout=30):
                captured_requests.append(req)
                resp = MagicMock()
                resp.read.return_value = json.dumps({"id": "task_img_1"}).encode("utf-8")
                resp.__enter__.return_value = resp
                return resp

            mock_urlopen.side_effect = fake_urlopen

            client = NormaVideoClient(api_key="nr_hub_test")
            task = client.create_task(
                prompt="Animate this image",
                image_path=tf_path,
            )

            self.assertEqual(task.id, "task_img_1")
            self.assertEqual(len(captured_requests), 1)
            sent_data = json.loads(captured_requests[0].data.decode("utf-8"))
            self.assertIn("image_url", sent_data)
            self.assertTrue(sent_data["image_url"].startswith("data:image/png;base64,"))
        finally:
            tf_path.unlink(missing_ok=True)

    @patch("urllib.request.urlopen")
    def test_create_task_with_image_url(self, mock_urlopen):
        captured_requests = []

        def fake_urlopen(req, timeout=30):
            captured_requests.append(req)
            resp = MagicMock()
            resp.read.return_value = json.dumps({"id": "task_url_1"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        mock_urlopen.side_effect = fake_urlopen

        client = NormaVideoClient(api_key="nr_hub_test")
        task = client.create_task(
            prompt="Animate url image",
            image_url="https://example.com/art.jpg",
        )

        self.assertEqual(task.id, "task_url_1")
        sent_data = json.loads(captured_requests[0].data.decode("utf-8"))
        self.assertEqual(sent_data["image_url"], "https://example.com/art.jpg")

    @patch("urllib.request.urlopen")
    @patch("time.sleep", return_value=None)
    def test_retry_on_502_success(self, mock_sleep, mock_urlopen):
        # First call raises 502, second call returns valid json
        err_502 = urllib.error.HTTPError(
            url="http://api.normahub.cc/v1/videos/generations",
            code=502,
            msg="Bad Gateway",
            hdrs={},
            fp=io.BytesIO(b'{"error":{"message":"Bad Gateway"}}'),
        )
        success_resp = MagicMock()
        success_resp.read.return_value = json.dumps({"id": "task_retried"}).encode("utf-8")
        success_resp.__enter__.return_value = success_resp

        mock_urlopen.side_effect = [err_502, success_resp]

        client = NormaVideoClient(api_key="nr_hub_test", max_retries=3)
        task = client.create_task(prompt="Test retry")
        self.assertEqual(task.id, "task_retried")
        self.assertEqual(mock_sleep.call_count, 1)

    @patch("urllib.request.urlopen")
    @patch("time.sleep", return_value=None)
    def test_retry_exhausted_raises_error(self, mock_sleep, mock_urlopen):
        err_503 = urllib.error.HTTPError(
            url="http://api.normahub.cc/v1/videos/generations",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=io.BytesIO(b'{"error":{"message":"Down"}}'),
        )
        mock_urlopen.side_effect = [err_503, err_503, err_503]

        client = NormaVideoClient(api_key="nr_hub_test", max_retries=3)
        with self.assertRaises(NormaVideoError):
            client.create_task(prompt="Test retry failure")
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("urllib.request.urlopen")
    @patch("time.sleep", return_value=None)
    def test_wait_for_completion(self, mock_sleep, mock_urlopen):
        resp_proc = MagicMock()
        resp_proc.read.return_value = json.dumps({
            "id": "t1", "status": "processing", "model": "seedance-2.5", "prompt": "test",
        }).encode("utf-8")
        resp_proc.__enter__.return_value = resp_proc

        resp_comp = MagicMock()
        resp_comp.read.return_value = json.dumps({
            "id": "t1", "status": "completed", "model": "seedance-2.5", "prompt": "test",
            "video_url": "https://api.normahub.cc/v.mp4",
        }).encode("utf-8")
        resp_comp.__enter__.return_value = resp_comp

        mock_urlopen.side_effect = [resp_proc, resp_comp]

        client = NormaVideoClient(api_key="nr_hub_test")
        callbacks = []
        task = client.wait_for_completion("t1", progress_callback=lambda t: callbacks.append(t.status))

        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertEqual(task.video_url, "https://api.normahub.cc/v.mp4")
        self.assertEqual(callbacks, [TaskStatus.PROCESSING, TaskStatus.COMPLETED])

    @patch("urllib.request.urlopen")
    @patch("time.sleep", return_value=None)
    def test_wait_for_completion_failure(self, mock_sleep, mock_urlopen):
        resp_failed = MagicMock()
        resp_failed.read.return_value = json.dumps({
            "id": "t1", "status": "failed", "model": "seedance-2.5", "error": "Render error",
        }).encode("utf-8")
        resp_failed.__enter__.return_value = resp_failed
        mock_urlopen.return_value = resp_failed

        client = NormaVideoClient(api_key="nr_hub_test")
        with self.assertRaises(VideoGenerationFailedError):
            client.wait_for_completion("t1")

    @patch("urllib.request.urlopen")
    def test_budget_exceeded_error(self, mock_urlopen):
        err_429 = urllib.error.HTTPError(
            url="http://api.normahub.cc/v1/videos",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=io.BytesIO(b'{"error":{"message":"Spend limit exceeded","code":"budget_exceeded"}}'),
        )
        mock_urlopen.side_effect = err_429

        client = NormaVideoClient(api_key="nr_hub_test", max_retries=1)
        with self.assertRaises(BudgetExceededError):
            client.create_task(prompt="Exceed budget")

    @patch("urllib.request.urlopen")
    def test_model_not_allowed_error(self, mock_urlopen):
        err_403 = urllib.error.HTTPError(
            url="http://api.normahub.cc/v1/videos",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=io.BytesIO(b'{"error":{"message":"Model not allowed for this key","code":"model_not_allowed"}}'),
        )
        mock_urlopen.side_effect = err_403

        client = NormaVideoClient(api_key="nr_hub_test", max_retries=1)
        with self.assertRaises(ModelNotAllowedError):
            client.create_task(prompt="Forbidden model")

    @patch("urllib.request.urlopen")
    def test_x_request_id_captured(self, mock_urlopen):
        resp_mock = MagicMock()
        resp_mock.read.return_value = json.dumps({
            "id": "task_req_123", "status": "pending", "model": "seedance-2.5", "prompt": "test",
        }).encode("utf-8")
        resp_mock.headers = {"X-Request-Id": "nh_req_789abc"}
        resp_mock.__enter__.return_value = resp_mock
        mock_urlopen.return_value = resp_mock

        client = NormaVideoClient(api_key="nr_hub_test")
        task = client.create_task(prompt="Track request")
        self.assertEqual(task.id, "task_req_123")
        self.assertEqual(task.request_id, "nh_req_789abc")



class TestAsyncNormaVideoClient(unittest.IsolatedAsyncioTestCase):
    async def test_async_missing_api_key_raises_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(AuthenticationError):
                AsyncNormaVideoClient(api_key="")

    async def test_async_client_init_with_key(self):
        client = AsyncNormaVideoClient(api_key="nr_hub_async_123")
        self.assertEqual(client.api_key, "nr_hub_async_123")
        self.assertEqual(client.base_url, "https://api.normahub.cc/v1")
        self.assertEqual(client.max_retries, 3)

    @patch("urllib.request.urlopen")
    async def test_async_create_task(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "id": "task_async_99",
            "status": "pending",
            "model": "seedance-2.5",
        }).encode("utf-8")
        resp.__enter__.return_value = resp
        mock_urlopen.return_value = resp

        client = AsyncNormaVideoClient(api_key="nr_hub_async_123")
        task = await client.create_task(
            prompt="Deep underwater reef",
            model=VideoModel.SEEDANCE_2_5,
        )

        self.assertEqual(task.id, "task_async_99")
        self.assertEqual(task.status, TaskStatus.PENDING)

    @patch("urllib.request.urlopen")
    async def test_async_create_task_with_image(self, mock_urlopen):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
            tf.write(b"\xff\xd8\xfffake_jpg")
            tf_path = Path(tf.name)

        try:
            captured_requests = []

            def fake_urlopen(req, timeout=30):
                captured_requests.append(req)
                resp = MagicMock()
                resp.read.return_value = json.dumps({"id": "task_i2v_async"}).encode("utf-8")
                resp.__enter__.return_value = resp
                return resp

            mock_urlopen.side_effect = fake_urlopen

            client = AsyncNormaVideoClient(api_key="nr_hub_async_123")
            task = await client.create_task(
                prompt="Animate portrait",
                image_path=tf_path,
            )

            self.assertEqual(task.id, "task_i2v_async")
            sent_data = json.loads(captured_requests[0].data.decode("utf-8"))
            self.assertTrue(sent_data["image_url"].startswith("data:image/jpeg;base64,"))
        finally:
            tf_path.unlink(missing_ok=True)

    @patch("urllib.request.urlopen")
    async def test_async_get_status(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "id": "task_status_check",
            "status": "processing",
            "model": "seedance-2.5",
            "prompt": "Test async status",
        }).encode("utf-8")
        resp.__enter__.return_value = resp
        mock_urlopen.return_value = resp

        client = AsyncNormaVideoClient(api_key="nr_hub_async_123")
        task = await client.get_status("task_status_check")

        self.assertEqual(task.id, "task_status_check")
        self.assertEqual(task.status, TaskStatus.PROCESSING)

    @patch("urllib.request.urlopen")
    @patch("asyncio.sleep", return_value=None)
    async def test_async_wait_for_completion(self, mock_sleep, mock_urlopen):
        resp_proc = MagicMock()
        resp_proc.read.return_value = json.dumps({
            "id": "t_async", "status": "processing",
        }).encode("utf-8")
        resp_proc.__enter__.return_value = resp_proc

        resp_comp = MagicMock()
        resp_comp.read.return_value = json.dumps({
            "id": "t_async", "status": "completed", "video_url": "https://api.normahub.cc/async.mp4",
        }).encode("utf-8")
        resp_comp.__enter__.return_value = resp_comp

        mock_urlopen.side_effect = [resp_proc, resp_comp]

        client = AsyncNormaVideoClient(api_key="nr_hub_async_123")
        progress_calls = []

        async def async_cb(task: VideoTask):
            progress_calls.append(task.status)

        finished = await client.wait_for_completion("t_async", progress_callback=async_cb)
        self.assertEqual(finished.status, TaskStatus.COMPLETED)
        self.assertEqual(finished.video_url, "https://api.normahub.cc/async.mp4")
        self.assertEqual(progress_calls, [TaskStatus.PROCESSING, TaskStatus.COMPLETED])

    @patch("urllib.request.urlopen")
    @patch("asyncio.sleep", return_value=None)
    async def test_async_retry_on_503(self, mock_sleep, mock_urlopen):
        err_503 = urllib.error.HTTPError(
            url="http://api.normahub.cc/v1/videos/generations",
            code=503,
            msg="Gateway Unavailable",
            hdrs={},
            fp=io.BytesIO(b'{"error":{"message":"Unavailable"}}'),
        )
        resp_ok = MagicMock()
        resp_ok.read.return_value = json.dumps({"id": "task_after_503"}).encode("utf-8")
        resp_ok.__enter__.return_value = resp_ok

        mock_urlopen.side_effect = [err_503, resp_ok]

        client = AsyncNormaVideoClient(api_key="nr_hub_async_123", max_retries=3)
        task = await client.create_task(prompt="Retry async")
        self.assertEqual(task.id, "task_after_503")
        self.assertEqual(mock_sleep.call_count, 1)

    @patch("urllib.request.urlopen")
    async def test_async_download_video(self, mock_urlopen):
        resp = MagicMock()
        resp.read.side_effect = [b"video chunk 1", b"video chunk 2", b""]
        resp.__enter__.return_value = resp
        mock_urlopen.return_value = resp

        client = AsyncNormaVideoClient(api_key="nr_hub_async_123")
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "sub" / "downloaded.mp4"
            saved_path = await client.download_video("https://api.normahub.cc/v.mp4", out_file)
            self.assertTrue(saved_path.is_file())
            self.assertEqual(saved_path.read_bytes(), b"video chunk 1video chunk 2")


class TestImageEncoding(unittest.TestCase):
    def test_encode_png(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tf.write(b"png_content")
            p = Path(tf.name)

        try:
            uri = encode_image_to_data_uri(p)
            self.assertTrue(uri.startswith("data:image/png;base64,"))
        finally:
            p.unlink(missing_ok=True)

    def test_encode_jpeg(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
            tf.write(b"jpg_content")
            p = Path(tf.name)

        try:
            uri = encode_image_to_data_uri(p)
            self.assertTrue(uri.startswith("data:image/jpeg;base64,"))
        finally:
            p.unlink(missing_ok=True)

    def test_encode_missing_file_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            encode_image_to_data_uri(Path("/nonexistent/image_12345.png"))


class TestCLI(unittest.TestCase):
    def test_cli_help(self):
        with self.assertRaises(SystemExit) as cm:
            with patch("sys.argv", ["seedance", "--help"]):
                cli_main()
        self.assertEqual(cm.exception.code, 0)

    @patch("seedance.cli.NormaVideoClient")
    def test_cli_image_argument_parsing(self, mock_client_cls):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.create_task.return_value = MagicMock(id="cli_task_1")
        mock_instance.wait_for_completion.return_value = MagicMock(
            id="cli_task_1",
            video_url="https://api.normahub.cc/v.mp4",
        )
        temp_out = tempfile.NamedTemporaryFile(delete=False)
        temp_out.write(b"dummy")
        temp_out.close()
        mock_instance.download_video.return_value = Path(temp_out.name)

        try:
            with patch("sys.argv", [
                "seedance",
                "Cinematic shot",
                "-i", "https://example.com/input.png",
                "-o", temp_out.name,
                "--api-key", "nr_hub_key",
            ]):
                exit_code = cli_main()
                self.assertEqual(exit_code, 0)
                mock_instance.create_task.assert_called_once()
                call_kwargs = mock_instance.create_task.call_args[1]
                self.assertEqual(call_kwargs["image_url"], "https://example.com/input.png")
        finally:
            Path(temp_out.name).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

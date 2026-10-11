"""
Core Client implementation for NormaHub SeeDance & Grok Video API.
Zero external dependencies (uses standard library urllib & asyncio).
"""

import asyncio
import base64
import json
import mimetypes
import os
import random
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from .exceptions import (
    AuthenticationError,
    BudgetExceededError,
    InsufficientBalanceError,
    ModelNotAllowedError,
    NormaVideoError,
    ProviderUnavailableError,
    RateLimitError,
    VideoGenerationFailedError,
    VideoGenerationTimeoutError,
)
from .types import TaskStatus, VideoModel, VideoTask

RETRYABLE_STATUS_CODES = {502, 503, 524}


def encode_image_to_data_uri(image_path: Union[str, Path]) -> str:
    """Encodes a local image file into a base64 data URI."""
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image file not found: {path}")

    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type or not mime_type.startswith("image/"):
        ext = path.suffix.lower().lstrip(".")
        if ext in ("jpg", "jpeg"):
            mime_type = "image/jpeg"
        elif ext == "png":
            mime_type = "image/png"
        elif ext == "webp":
            mime_type = "image/webp"
        elif ext == "gif":
            mime_type = "image/gif"
        else:
            mime_type = "image/jpeg"

    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


class NormaVideoClient:
    """Client for generating videos with SeeDance & Grok models via NormaHub."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.api_key = api_key or os.getenv("NORMAHUB_API_KEY")
        if not self.api_key:
            raise AuthenticationError(
                "API key is required. Pass it via NormaVideoClient(api_key=...) "
                "or set the NORMAHUB_API_KEY environment variable. "
                "Get your key at https://normahub.cc"
            )

        self.base_url = (base_url or os.getenv("NORMAHUB_BASE_URL") or "https://api.normahub.cc/v1").rstrip("/")
        self.timeout = timeout
        self.max_retries = max(1, max_retries)

    def _execute_request(
        self,
        endpoint: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Performs a single HTTP request to NormaHub API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "NormaHub-SeeDance-PythonSDK/0.2.0",
            "Content-Type": "application/json",
        }

        data = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                req_id = response.headers.get("X-Request-Id")
                if req_id:
                    parsed["_request_id"] = req_id
            return parsed

    def _parse_http_error(self, e: urllib.error.HTTPError) -> Exception:
        """Parses urllib HTTPError into a structured NormaVideoError conforming to NormaHub docs."""
        error_body = e.read().decode("utf-8", errors="ignore")
        code = ""
        try:
            error_json = json.loads(error_body)
            msg = error_json.get("error", {}).get("message") or error_body
            code = error_json.get("error", {}).get("code", "")
        except Exception:
            msg = error_body or e.reason

        req_id = e.headers.get("X-Request-Id") if hasattr(e, "headers") else None
        req_suffix = f" [Request ID: {req_id}]" if req_id else ""

        if e.code == 401 or code == "invalid_api_key":
            return AuthenticationError(f"Invalid API key: {msg}{req_suffix}")
        elif e.code == 402 or code in ("insufficient_balance", "provider_balance_depleted"):
            return InsufficientBalanceError(
                f"Insufficient NormaHub balance. Please top up at https://normahub.cc: {msg}{req_suffix}"
            )
        elif code == "budget_exceeded" or (e.code == 429 and "budget" in str(msg).lower()):
            return BudgetExceededError(
                f"API key spend limit exceeded (budget_exceeded): {msg}. Increase limit at https://normahub.cc/dashboard{req_suffix}"
            )
        elif e.code == 429 or code == "rate_limit_exceeded":
            return RateLimitError(f"Rate limit exceeded (rate_limit_exceeded): {msg}{req_suffix}")
        elif e.code == 403 or code in ("model_not_allowed", "model_unavailable", "scope_not_allowed"):
            return ModelNotAllowedError(f"Model or scope not allowed for this API key: {msg}{req_suffix}")
        elif e.code == 503 or code in ("provider_unavailable", "provider_not_configured"):
            return ProviderUnavailableError(f"Provider temporarily unavailable: {msg}{req_suffix}")
        else:
            return NormaVideoError(f"API Error ({e.code}, {code or 'unknown'}): {msg}{req_suffix}")

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Performs HTTP request with automatic retry on network errors and 502/503/524."""
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return self._execute_request(endpoint, method=method, payload=payload)
            except urllib.error.HTTPError as e:
                if e.code in RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                    jitter = random.uniform(0.1, 0.4)
                    sleep_time = (0.5 * (2 ** (attempt - 1))) + jitter
                    time.sleep(sleep_time)
                    continue
                last_exception = self._parse_http_error(e)
                raise last_exception from e
            except (urllib.error.URLError, OSError, TimeoutError) as e:
                if attempt < self.max_retries:
                    jitter = random.uniform(0.1, 0.4)
                    sleep_time = (0.5 * (2 ** (attempt - 1))) + jitter
                    time.sleep(sleep_time)
                    continue
                reason = getattr(e, "reason", str(e))
                last_exception = NormaVideoError(f"Network error connecting to NormaHub: {reason}")
                raise last_exception from e

        if last_exception:
            raise last_exception
        raise NormaVideoError("Request failed after retries")

    def create_task(
        self,
        prompt: str,
        model: Union[VideoModel, str] = VideoModel.SEEDANCE_2_5,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_path: Optional[Union[str, Path]] = None,
        image_url: Optional[str] = None,
        **kwargs: Any,
    ) -> VideoTask:
        """Submits an asynchronous video generation task.

        Supports Text-to-Video and Image-to-Video.
        Returns immediately with a pending VideoTask.
        """
        model_name = model.value if isinstance(model, VideoModel) else str(model)
        payload = {
            "model": model_name,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            **kwargs,
        }

        final_image_url = image_url
        if image_path:
            final_image_url = encode_image_to_data_uri(image_path)

        if final_image_url:
            payload["image_url"] = final_image_url

        try:
            resp = self._request("videos", method="POST", payload=payload)
        except NormaVideoError as e:
            if "404" in str(e):
                resp = self._request("videos/generations", method="POST", payload=payload)
            else:
                raise

        task_id = resp.get("id") or resp.get("task_id")
        if not task_id:
            raise NormaVideoError(f"Server did not return a valid task ID: {resp}")

        return VideoTask(
            id=task_id,
            model=model_name,
            prompt=prompt,
            status=TaskStatus(resp.get("status", "pending")),
            created_at=int(resp.get("created_at", time.time())),
            video_url=resp.get("video_url") or resp.get("url"),
            request_id=resp.get("_request_id"),
            raw_response=resp,
        )

    def get_status(self, task_id: str) -> VideoTask:
        """Polls current status of a specific video generation task."""
        try:
            resp = self._request(f"videos/status/{task_id}", method="GET")
        except NormaVideoError as e:
            if "404" in str(e):
                resp = self._request(f"videos/tasks/{task_id}", method="GET")
            else:
                raise

        status_raw = resp.get("status", "pending")
        try:
            status = TaskStatus(status_raw)
        except ValueError:
            status = TaskStatus.PROCESSING

        return VideoTask(
            id=task_id,
            model=resp.get("model", "unknown"),
            prompt=resp.get("prompt", ""),
            status=status,
            created_at=int(resp.get("created_at", time.time())),
            video_url=resp.get("video_url") or resp.get("url"),
            error=resp.get("error"),
            request_id=resp.get("_request_id"),
            raw_response=resp,
        )

    def wait_for_completion(
        self,
        task_id: str,
        timeout: int = 300,
        initial_poll_interval: float = 3.0,
        progress_callback: Optional[Callable[[VideoTask], None]] = None,
    ) -> VideoTask:
        """Polls task until completion, failure, or timeout.

        Implements exponential backoff with jitter.
        """
        start_time = time.monotonic()
        poll_interval = initial_poll_interval

        while True:
            task = self.get_status(task_id)

            if progress_callback:
                progress_callback(task)

            if task.status == TaskStatus.COMPLETED:
                return task

            if task.status in (TaskStatus.FAILED, TaskStatus.CANCELLED):
                raise VideoGenerationFailedError(
                    f"Video generation task {task_id} failed: {task.error or 'Unknown error'}"
                )

            if time.monotonic() - start_time > timeout:
                raise VideoGenerationTimeoutError(
                    f"Video task {task_id} timed out after {timeout} seconds"
                )

            # Sleep with jitter (±15%)
            jitter = random.uniform(0.85, 1.15)
            time.sleep(poll_interval * jitter)
            poll_interval = min(poll_interval * 1.25, 10.0)

    def download_video(self, video_url: str, output_path: Union[str, Path]) -> Path:
        """Downloads the rendered video file to the specified local path with retries."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        req = urllib.request.Request(
            video_url,
            headers={"User-Agent": "NormaHub-SeeDance-PythonSDK/0.2.0"},
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp, open(target, "wb") as f:
                    while chunk := resp.read(64 * 1024):
                        f.write(chunk)
                return target
            except urllib.error.HTTPError as e:
                if e.code in RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                    jitter = random.uniform(0.1, 0.4)
                    time.sleep((0.5 * (2 ** (attempt - 1))) + jitter)
                    continue
                raise NormaVideoError(f"Failed to download video (HTTP {e.code}): {e.reason}") from e
            except (urllib.error.URLError, OSError, TimeoutError) as e:
                if attempt < self.max_retries:
                    jitter = random.uniform(0.1, 0.4)
                    time.sleep((0.5 * (2 ** (attempt - 1))) + jitter)
                    continue
                reason = getattr(e, "reason", str(e))
                raise NormaVideoError(f"Network error downloading video: {reason}") from e

        return target

    def generate_and_download(
        self,
        prompt: str,
        output_path: Union[str, Path],
        model: Union[VideoModel, str] = VideoModel.SEEDANCE_2_5,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_path: Optional[Union[str, Path]] = None,
        image_url: Optional[str] = None,
        timeout: int = 300,
        progress_callback: Optional[Callable[[VideoTask], None]] = None,
        **kwargs: Any,
    ) -> Path:
        """High-level method: Submits task, waits for rendering, downloads MP4."""
        task = self.create_task(
            prompt=prompt,
            model=model,
            duration=duration,
            aspect_ratio=aspect_ratio,
            image_path=image_path,
            image_url=image_url,
            **kwargs,
        )
        finished_task = self.wait_for_completion(
            task.id,
            timeout=timeout,
            progress_callback=progress_callback,
        )

        if not finished_task.video_url:
            raise VideoGenerationFailedError("Video completed but no download URL was returned")

        return self.download_video(finished_task.video_url, output_path)


class AsyncNormaVideoClient:
    """Asynchronous client for generating videos with SeeDance & Grok models via NormaHub."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self._sync_client = NormaVideoClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.api_key = self._sync_client.api_key
        self.base_url = self._sync_client.base_url
        self.timeout = self._sync_client.timeout
        self.max_retries = self._sync_client.max_retries

    async def _request(
        self,
        endpoint: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Performs async HTTP request with non-blocking retry on network errors and 502/503/524."""
        loop = asyncio.get_running_loop()
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return await loop.run_in_executor(
                    None,
                    self._sync_client._execute_request,
                    endpoint,
                    method,
                    payload,
                )
            except urllib.error.HTTPError as e:
                if e.code in RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                    jitter = random.uniform(0.1, 0.4)
                    sleep_time = (0.5 * (2 ** (attempt - 1))) + jitter
                    await asyncio.sleep(sleep_time)
                    continue
                last_exception = self._sync_client._parse_http_error(e)
                raise last_exception from e
            except (urllib.error.URLError, OSError, TimeoutError) as e:
                if attempt < self.max_retries:
                    jitter = random.uniform(0.1, 0.4)
                    sleep_time = (0.5 * (2 ** (attempt - 1))) + jitter
                    await asyncio.sleep(sleep_time)
                    continue
                reason = getattr(e, "reason", str(e))
                last_exception = NormaVideoError(f"Network error connecting to NormaHub: {reason}")
                raise last_exception from e

        if last_exception:
            raise last_exception
        raise NormaVideoError("Request failed after retries")

    async def create_task(
        self,
        prompt: str,
        model: Union[VideoModel, str] = VideoModel.SEEDANCE_2_5,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_path: Optional[Union[str, Path]] = None,
        image_url: Optional[str] = None,
        **kwargs: Any,
    ) -> VideoTask:
        """Submits an asynchronous video generation task.

        Supports Text-to-Video and Image-to-Video.
        Returns immediately with a pending VideoTask.
        """
        model_name = model.value if isinstance(model, VideoModel) else str(model)
        payload = {
            "model": model_name,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            **kwargs,
        }

        final_image_url = image_url
        if image_path:
            final_image_url = encode_image_to_data_uri(image_path)

        if final_image_url:
            payload["image_url"] = final_image_url

        try:
            resp = await self._request("videos", method="POST", payload=payload)
        except NormaVideoError as e:
            if "404" in str(e):
                resp = await self._request("videos/generations", method="POST", payload=payload)
            else:
                raise

        task_id = resp.get("id") or resp.get("task_id")
        if not task_id:
            raise NormaVideoError(f"Server did not return a valid task ID: {resp}")

        return VideoTask(
            id=task_id,
            model=model_name,
            prompt=prompt,
            status=TaskStatus(resp.get("status", "pending")),
            created_at=int(resp.get("created_at", time.time())),
            video_url=resp.get("video_url") or resp.get("url"),
            request_id=resp.get("_request_id"),
            raw_response=resp,
        )

    async def get_status(self, task_id: str) -> VideoTask:
        """Polls current status of a specific video generation task asynchronously."""
        try:
            resp = await self._request(f"videos/status/{task_id}", method="GET")
        except NormaVideoError as e:
            if "404" in str(e):
                resp = await self._request(f"videos/tasks/{task_id}", method="GET")
            else:
                raise

        status_raw = resp.get("status", "pending")
        try:
            status = TaskStatus(status_raw)
        except ValueError:
            status = TaskStatus.PROCESSING

        return VideoTask(
            id=task_id,
            model=resp.get("model", "unknown"),
            prompt=resp.get("prompt", ""),
            status=status,
            created_at=int(resp.get("created_at", time.time())),
            video_url=resp.get("video_url") or resp.get("url"),
            error=resp.get("error"),
            request_id=resp.get("_request_id"),
            raw_response=resp,
        )

    async def wait_for_completion(
        self,
        task_id: str,
        timeout: int = 300,
        initial_poll_interval: float = 3.0,
        progress_callback: Optional[Callable[[VideoTask], Any]] = None,
    ) -> VideoTask:
        """Polls task until completion, failure, or timeout with non-blocking sleep.

        Implements exponential backoff with jitter.
        """
        start_time = time.monotonic()
        poll_interval = initial_poll_interval

        while True:
            task = await self.get_status(task_id)

            if progress_callback:
                res = progress_callback(task)
                if asyncio.iscoroutine(res):
                    await res

            if task.status == TaskStatus.COMPLETED:
                return task

            if task.status in (TaskStatus.FAILED, TaskStatus.CANCELLED):
                raise VideoGenerationFailedError(
                    f"Video generation task {task_id} failed: {task.error or 'Unknown error'}"
                )

            if time.monotonic() - start_time > timeout:
                raise VideoGenerationTimeoutError(
                    f"Video task {task_id} timed out after {timeout} seconds"
                )

            # Sleep with jitter (±15%)
            jitter = random.uniform(0.85, 1.15)
            await asyncio.sleep(poll_interval * jitter)
            poll_interval = min(poll_interval * 1.25, 10.0)

    async def download_video(self, video_url: str, output_path: Union[str, Path]) -> Path:
        """Downloads the rendered video file to the specified local path asynchronously."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._sync_client.download_video,
            video_url,
            output_path,
        )

    async def generate_and_download(
        self,
        prompt: str,
        output_path: Union[str, Path],
        model: Union[VideoModel, str] = VideoModel.SEEDANCE_2_5,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        image_path: Optional[Union[str, Path]] = None,
        image_url: Optional[str] = None,
        timeout: int = 300,
        progress_callback: Optional[Callable[[VideoTask], Any]] = None,
        **kwargs: Any,
    ) -> Path:
        """High-level async method: Submits task, waits for rendering, downloads MP4."""
        task = await self.create_task(
            prompt=prompt,
            model=model,
            duration=duration,
            aspect_ratio=aspect_ratio,
            image_path=image_path,
            image_url=image_url,
            **kwargs,
        )
        finished_task = await self.wait_for_completion(
            task.id,
            timeout=timeout,
            progress_callback=progress_callback,
        )

        if not finished_task.video_url:
            raise VideoGenerationFailedError("Video completed but no download URL was returned")

        return await self.download_video(finished_task.video_url, output_path)

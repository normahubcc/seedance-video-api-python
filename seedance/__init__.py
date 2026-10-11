"""
NormaHub SeeDance & Grok Video Python SDK.
Fast, reliable video generation in Russia without VPN and with RUB payment.
"""

from .client import AsyncNormaVideoClient, NormaVideoClient, encode_image_to_data_uri
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

__version__ = "0.2.0"
__all__ = [
    "NormaVideoClient",
    "AsyncNormaVideoClient",
    "encode_image_to_data_uri",
    "VideoModel",
    "TaskStatus",
    "VideoTask",
    "NormaVideoError",
    "AuthenticationError",
    "BudgetExceededError",
    "InsufficientBalanceError",
    "ModelNotAllowedError",
    "ProviderUnavailableError",
    "RateLimitError",
    "VideoGenerationFailedError",
    "VideoGenerationTimeoutError",
]

"""
Exceptions for NormaHub Video Generation API.
"""


class NormaVideoError(Exception):
    """Base exception for all NormaHub Video SDK errors."""
    pass


class AuthenticationError(NormaVideoError):
    """Raised when the provided API key is invalid or missing."""
    pass


class InsufficientBalanceError(NormaVideoError):
    """Raised when there are not enough funds on the NormaHub balance."""
    pass


class RateLimitError(NormaVideoError):
    """Raised when requests exceed frequency rate limits (HTTP 429 rate_limit_exceeded)."""
    pass


class BudgetExceededError(NormaVideoError):
    """Raised when API key spend limit is reached (HTTP 429 budget_exceeded)."""
    pass


class ModelNotAllowedError(NormaVideoError):
    """Raised when the model is not allowed or certified for the key (HTTP 403 model_not_allowed)."""
    pass


class ProviderUnavailableError(NormaVideoError):
    """Raised when the upstream provider or model is temporarily unavailable (HTTP 503)."""
    pass


class VideoGenerationFailedError(NormaVideoError):
    """Raised when the video generation task fails on upstream model."""
    pass


class VideoGenerationTimeoutError(NormaVideoError):
    """Raised when polling exceeds the configured timeout."""
    pass

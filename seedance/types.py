"""
Data classes and types for NormaHub Video Generation API.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class VideoModel(str, Enum):
    SEEDANCE_2_5 = "seedance-2.5"
    SEEDANCE_2_0 = "seedance-2.0"
    SEEDANCE_2_0_FAST = "seedance-2.0-fast"
    SEEDANCE_2_0_MINI = "seedance-2.0-mini"
    GROK_IMAGINE_VIDEO_1_5 = "grok-imagine-video-1.5"
    GROK_IMAGINE_VIDEO = "grok-imagine-video"


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class VideoTask:
    id: str
    model: str
    prompt: str
    status: TaskStatus
    created_at: int
    video_url: Optional[str] = None
    error: Optional[str] = None
    request_id: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_finished(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    @property
    def is_successful(self) -> bool:
        return self.status == TaskStatus.COMPLETED and bool(self.video_url)

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
from numpy.typing import NDArray

RGBFrame = NDArray[np.uint8]


@dataclass(frozen=True)
class CameraStatus:
    is_connected: bool
    is_preview_active: bool
    camera_name: str
    has_errors: bool = False
    error_message: str | None = None
    is_mock: bool = False


@dataclass(frozen=True)
class Frame:
    image: RGBFrame
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    camera_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

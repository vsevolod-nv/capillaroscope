from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from capillaroscope_app.domain.models import CameraStatus, Frame
from capillaroscope_app.hardware.camera_base import CameraBase, CameraConnectionError

MOCK_PHOTOS_DIR = (
    Path(__file__).resolve().parents[2] / "media" / "mock_camera" / "photos"
)
PREVIEW_IMAGE_EXTENSIONS = frozenset({".bmp", ".jpeg", ".jpg", ".png"})


class MockCamera(CameraBase):
    def __init__(
        self,
        reason: str = "Real camera is not available",
        preview_image_path: Path | None = None,
    ) -> None:
        self._reason = reason
        self._connected = False
        self._preview_active = False
        self._preview_image_path = preview_image_path or self._find_preview_image()
        self._frame = self._load_preview_frame()

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._preview_active = False
        self._connected = False

    def start_preview(self) -> None:
        if not self._connected:
            self.connect()
        self._preview_active = True

    def stop_preview(self) -> None:
        self._preview_active = False

    def capture_frame(self) -> Frame:
        if not self._preview_active:
            self.start_preview()
        return Frame(
            image=self._frame.copy(),
            timestamp=datetime.now(timezone.utc),
            camera_name="Mock Camera",
            metadata={
                "reason": self._reason,
                "source": "static-image",
                "image_path": str(self._preview_image_path),
            },
        )

    def get_status(self) -> CameraStatus:
        return CameraStatus(
            is_connected=self._connected,
            is_preview_active=self._preview_active,
            camera_name="Mock Camera",
            has_errors=True,
            error_message=self._reason,
            is_mock=True,
        )

    def _find_preview_image(self) -> Path | None:
        if not MOCK_PHOTOS_DIR.is_dir():
            return None

        for path in sorted(MOCK_PHOTOS_DIR.iterdir()):
            if path.is_file() and path.suffix.lower() in PREVIEW_IMAGE_EXTENSIONS:
                return path
        return None

    def _load_preview_frame(self) -> np.ndarray:
        if self._preview_image_path is None:
            raise CameraConnectionError(
                f"No mock preview image found in {MOCK_PHOTOS_DIR}"
            )

        image = self._read_image(self._preview_image_path)
        if image is None:
            raise CameraConnectionError(
                f"Could not read mock preview image: {self._preview_image_path}"
            )
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def _read_image(self, image_path: Path) -> np.ndarray | None:
        """Read an image without OpenCV's Windows Unicode-path limitation."""
        try:
            encoded_image = np.fromfile(image_path, dtype=np.uint8)
            if encoded_image.size == 0:
                return None
            return cv2.imdecode(encoded_image, cv2.IMREAD_COLOR)
        except (OSError, cv2.error):
            return None

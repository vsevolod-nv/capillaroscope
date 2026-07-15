from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from capillaroscope_app.domain.models import CameraStatus, Frame
from capillaroscope_app.hardware.camera_base import CameraBase


class MockCamera(CameraBase):
    def __init__(
        self,
        reason: str = "Real camera is not available",
        width: int = 960,
        height: int = 720,
    ) -> None:
        self._reason = reason
        self._width = width
        self._height = height
        self._connected = False
        self._preview_active = False
        self._frame = self._build_frame()

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
            metadata={"reason": self._reason},
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

    def _build_frame(self) -> np.ndarray:
        y, x = np.mgrid[0 : self._height, 0 : self._width]
        cx = self._width / 2
        cy = self._height / 2
        distance = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        vignette = np.clip(255 - distance * 0.35, 35, 255).astype(np.uint8)

        image = np.zeros((self._height, self._width, 3), dtype=np.uint8)
        image[..., 0] = vignette
        image[..., 1] = np.clip(vignette * 0.92, 0, 255).astype(np.uint8)
        image[..., 2] = np.clip(vignette * 0.82, 0, 255).astype(np.uint8)

        grid = ((x // 48) + (y // 48)) % 2 == 0
        image[grid] = np.clip(image[grid] + 18, 0, 255)

        self._draw_reticle(image)
        self._draw_label(image)
        return image

    def _draw_reticle(self, image: np.ndarray) -> None:
        center_y = self._height // 2
        center_x = self._width // 2
        color = np.array([30, 220, 170], dtype=np.uint8)
        image[center_y - 1 : center_y + 2, center_x - 160 : center_x + 160] = color
        image[center_y - 120 : center_y + 120, center_x - 1 : center_x + 2] = color
        radius = 145
        y, x = np.ogrid[: self._height, : self._width]
        ring = np.abs((x - center_x) ** 2 + (y - center_y) ** 2 - radius**2) < 600
        image[ring] = color

    def _draw_label(self, image: np.ndarray) -> None:
        # A compact block label avoids depending on font rendering packages.
        top = 26
        left = 28
        image[top : top + 78, left : left + 360] = np.array(
            [18, 25, 33],
            dtype=np.uint8,
        )
        image[top + 8 : top + 70, left + 8 : left + 352] = np.array(
            [45, 60, 74], dtype=np.uint8
        )

        stripes = [
            (18, 22, 260),
            (34, 22, 190),
            (50, 22, 315),
        ]
        for row, col, width in stripes:
            image[
                top + row : top + row + 7,
                left + col : left + col + width,
            ] = np.array(
                [220, 235, 245],
                dtype=np.uint8,
            )

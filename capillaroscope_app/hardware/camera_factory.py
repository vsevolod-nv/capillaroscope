from __future__ import annotations

import os

from capillaroscope_app.hardware.camera_base import CameraBase, CameraError
from capillaroscope_app.hardware.mindvision_camera import MindVisionCamera
from capillaroscope_app.hardware.mock_camera import MockCamera
from capillaroscope_app.hardware.opencv_camera import OpenCVCamera


def create_preview_camera() -> CameraBase:
    requested = os.getenv("CAPILLAROSCOPE_CAMERA", "auto").lower()
    if requested == "mock":
        camera = MockCamera("Mock camera forced by CAPILLAROSCOPE_CAMERA=mock")
        camera.connect()
        camera.start_preview()
        return camera

    errors: list[str] = []
    candidates: list[CameraBase] = []
    if requested in {"auto", "mindvision"}:
        candidates.append(MindVisionCamera())
    if requested == "opencv":
        candidates.append(OpenCVCamera(index=0))

    for candidate in candidates:
        try:
            candidate.connect()
            candidate.start_preview()
            return candidate
        except CameraError as exc:
            candidate.disconnect()
            errors.append(str(exc))

    reason = " | ".join(errors) if errors else "No camera adapter was selected"
    camera = MockCamera(reason=f"Using mock preview: {reason}")
    camera.connect()
    camera.start_preview()
    return camera

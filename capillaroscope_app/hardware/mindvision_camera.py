from __future__ import annotations

import ctypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from capillaroscope_app.domain.models import CameraStatus, Frame
from capillaroscope_app.hardware.camera_base import (
    CameraBase,
    CameraCaptureError,
    CameraConnectionError,
)


class MindVisionCamera(CameraBase):
    def __init__(self, device_index: int = 0, sdk_path: Path | None = None) -> None:
        self._device_index = device_index
        self._sdk_path = sdk_path
        self._sdk: Any | None = None
        self._handle: int | None = None
        self._frame_buffer: int | None = None
        self._frame_buffer_size = 0
        self._mono = True
        self._camera_name = "MindVision MV-SUA501GM"
        self._preview_active = False
        self._last_error: str | None = None

    def connect(self) -> None:
        sdk = self._load_sdk()
        self._sdk = sdk
        devices = sdk.CameraEnumerateDevice()
        if len(devices) == 0:
            raise CameraConnectionError("MindVision SDK did not find any camera")
        if self._device_index >= len(devices):
            raise CameraConnectionError(
                f"MindVision camera index {self._device_index} is out of range"
            )

        device = devices[self._device_index]
        self._camera_name = self._read_device_name(device)

        try:
            self._handle = sdk.CameraInit(device, -1, -1)
            capability = sdk.CameraGetCapability(self._handle)
            self._mono = bool(capability.sIspCapacity.bMonoSensor)
            output_format = (
                sdk.CAMERA_MEDIA_TYPE_MONO8
                if self._mono
                else sdk.CAMERA_MEDIA_TYPE_BGR8
            )
            sdk.CameraSetIspOutFormat(self._handle, output_format)
            sdk.CameraSetTriggerMode(self._handle, 0)
            sdk.CameraPlay(self._handle)

            max_width = capability.sResolutionRange.iWidthMax
            max_height = capability.sResolutionRange.iHeightMax
            channels = 1 if self._mono else 3
            self._frame_buffer_size = max_width * max_height * channels
            self._frame_buffer = sdk.CameraAlignMalloc(self._frame_buffer_size, 16)
        except Exception as exc:
            self.disconnect()
            message = f"MindVision camera init failed: {exc}"
            raise CameraConnectionError(message) from exc

        self._last_error = None

    def disconnect(self) -> None:
        self._preview_active = False
        if self._sdk is not None:
            if self._frame_buffer is not None:
                self._sdk.CameraAlignFree(self._frame_buffer)
                self._frame_buffer = None
            if self._handle is not None:
                self._sdk.CameraUnInit(self._handle)
                self._handle = None

    def start_preview(self) -> None:
        if self._handle is None:
            self.connect()
        self._preview_active = True

    def stop_preview(self) -> None:
        self._preview_active = False

    def capture_frame(self) -> Frame:
        if self._handle is None:
            self.connect()
        if not self._preview_active:
            self.start_preview()
        if self._sdk is None or self._frame_buffer is None or self._handle is None:
            raise CameraCaptureError("MindVision camera is not initialized")

        try:
            raw_data, frame_head = self._sdk.CameraGetImageBuffer(self._handle, 1000)
            self._sdk.CameraImageProcess(
                self._handle,
                raw_data,
                self._frame_buffer,
                frame_head,
            )
            self._sdk.CameraReleaseImageBuffer(self._handle, raw_data)
        except Exception as exc:
            self._last_error = f"MindVision frame capture failed: {exc}"
            raise CameraCaptureError(self._last_error) from exc

        width = frame_head.iWidth
        height = frame_head.iHeight
        channels = 1 if self._mono else 3
        byte_count = width * height * channels
        buffer_type = ctypes.c_ubyte * byte_count
        buffer = buffer_type.from_address(self._frame_buffer)
        frame = np.frombuffer(buffer, dtype=np.uint8).reshape(height, width, channels)

        if self._mono:
            rgb = np.repeat(frame, 3, axis=2)
        else:
            rgb = frame[..., ::-1].copy()

        return Frame(
            image=rgb,
            timestamp=datetime.now(timezone.utc),
            camera_name=self._camera_name,
            metadata={
                "source": "mindvision",
                "model": "MV-SUA501GM",
                "mono": self._mono,
            },
        )

    def get_status(self) -> CameraStatus:
        return CameraStatus(
            is_connected=self._handle is not None,
            is_preview_active=self._preview_active,
            camera_name=self._camera_name,
            has_errors=self._last_error is not None,
            error_message=self._last_error,
        )

    def _load_sdk(self) -> Any:
        searched_paths = self._prepare_sdk_paths()
        try:
            import mvsdk
        except (ImportError, OSError, AttributeError) as exc:
            paths = "; ".join(str(path) for path in searched_paths)
            raise CameraConnectionError(
                "MindVision SDK is not ready. Expected mvsdk.py and "
                f"MVCAMSDK_X64.dll. Searched SDK paths: {paths}. "
                f"Original error: {exc}"
            ) from exc
        return mvsdk

    def _prepare_sdk_paths(self) -> list[Path]:
        paths = self._candidate_sdk_paths()
        for path in reversed(paths):
            if path.exists():
                path_text = str(path)
                if path_text not in sys.path:
                    sys.path.insert(0, path_text)
                self._add_dll_directory(path)
        return paths

    def _candidate_sdk_paths(self) -> list[Path]:
        project_root = Path(__file__).resolve().parents[2]
        paths: list[Path] = []
        env_path = os.getenv("CAPILLAROSCOPE_MINDVISION_SDK_PATH")
        if env_path:
            paths.append(Path(env_path))
        if self._sdk_path is not None:
            paths.append(self._sdk_path)
        paths.extend(
            [
                project_root / "vendor" / "mindvision",
                project_root / "CameraSDK" / "demo" / "python_demo",
            ]
        )
        return paths

    def _add_dll_directory(self, path: Path) -> None:
        if not hasattr(os, "add_dll_directory"):
            return
        candidates = [
            path,
            path / "lib",
            path / "lib" / "x64",
            path / "bin",
            path / "bin" / "x64",
        ]
        for candidate in candidates:
            if candidate.exists():
                os.add_dll_directory(str(candidate))

    def _read_device_name(self, device: Any) -> str:
        get_name = getattr(device, "GetFriendlyName", None)
        if callable(get_name):
            return str(get_name())
        friendly_name = getattr(device, "acFriendlyName", None)
        if friendly_name:
            return str(friendly_name)
        return "MindVision MV-SUA501GM"

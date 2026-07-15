from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from capillaroscope_app.hardware.camera_base import CameraError  # noqa: E402
from capillaroscope_app.hardware.mindvision_camera import MindVisionCamera  # noqa: E402


def main() -> int:
    camera = MindVisionCamera()
    try:
        camera.connect()
    except CameraError as exc:
        print("MindVision check failed:")
        print(exc)
        return 1

    status = camera.get_status()
    print("MindVision check passed:")
    print(f"camera_name={status.camera_name}")
    print(f"is_connected={status.is_connected}")
    camera.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

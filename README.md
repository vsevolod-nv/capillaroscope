# capillaroscope

Desktop application for capillaroscope camera preview, acquisition, storage, and
image processing.

## Preview MVP

Recommended Windows setup:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the desktop preview:

```bash
python -m capillaroscope_app
```

If you do not use a virtual environment, make sure that dependencies are
installed into the same Python version that runs the app:

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 -m capillaroscope_app
```

Camera selection:

- `CAPILLAROSCOPE_CAMERA=auto` - try MindVision SDK, then mock.
- `CAPILLAROSCOPE_CAMERA=mindvision` - try only MindVision SDK, fallback to mock.
- `CAPILLAROSCOPE_CAMERA=opencv` - try generic OpenCV camera, fallback to mock.
- `CAPILLAROSCOPE_CAMERA=mock` - force mock camera.

The real camera adapter expects the MindVision Python SDK module `mvsdk` to be
available. If the SDK is missing, the app displays a mock preview automatically.
OpenCV is not used in `auto` mode to avoid accidentally showing a laptop webcam
instead of the industrial MindVision camera.

## MindVision SDK

For the `MV-SUA501GM-T1V-C` camera, the app looks for MindVision SDK files in:

- `vendor/mindvision`
- `CameraSDK/demo/python_demo`
- path from `CAPILLAROSCOPE_MINDVISION_SDK_PATH`

The Python wrapper is `mvsdk.py`. On Windows it also needs `MVCAMSDK_X64.dll`
available through the installed MindVision runtime, `PATH`, or the configured SDK
directory. The downloaded SDK archive is local machine setup material and is
ignored by Git.

Check SDK/runtime connectivity without starting the GUI:

```powershell
python scripts/check_mindvision_sdk.py
```

If the message says `MVCAMSDK_X64`, install the Windows MindVision Camera
Platform runtime/driver and make sure its DLL directory is available in `PATH`.

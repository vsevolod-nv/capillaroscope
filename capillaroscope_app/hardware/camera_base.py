from abc import ABC, abstractmethod

from capillaroscope_app.domain.models import CameraStatus, Frame


class CameraError(RuntimeError):
    """Base camera error raised by camera adapters."""


class CameraConnectionError(CameraError):
    """Raised when a camera adapter cannot connect to a device."""


class CameraCaptureError(CameraError):
    """Raised when a camera adapter cannot capture a frame."""


class CameraBase(ABC):
    @abstractmethod
    def connect(self) -> None:
        """Open hardware resources."""

    @abstractmethod
    def disconnect(self) -> None:
        """Release hardware resources."""

    @abstractmethod
    def start_preview(self) -> None:
        """Prepare camera for continuous preview capture."""

    @abstractmethod
    def stop_preview(self) -> None:
        """Stop continuous preview capture."""

    @abstractmethod
    def capture_frame(self) -> Frame:
        """Capture one RGB frame."""

    @abstractmethod
    def get_status(self) -> CameraStatus:
        """Return current camera status."""

    @abstractmethod
    def set_auto_exposure(self, enabled: bool) -> None:
        """Enable or disable camera auto exposure."""

    @abstractmethod
    def set_exposure_ms(self, exposure_ms: float) -> None:
        """Set manual exposure in milliseconds."""

    @abstractmethod
    def get_exposure_ms(self) -> float | None:
        """Return current exposure in milliseconds."""

    @abstractmethod
    def get_exposure_range_ms(self) -> tuple[float, float, float]:
        """Return min, max, step exposure in milliseconds."""

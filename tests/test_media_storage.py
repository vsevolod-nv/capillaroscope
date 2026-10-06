from pathlib import Path

import cv2
import numpy as np
import pytest

from capillaroscope_app.domain.models import Frame
from capillaroscope_app.storage.media_storage import MediaStorage, PhotoSaveError


def test_list_recent_photo_paths_returns_saved_photo_path(tmp_path: Path) -> None:
    storage = MediaStorage(project_root=tmp_path)
    frame = Frame(image=np.zeros((2, 2, 3), dtype=np.uint8))

    photo_path = storage.save_photo(frame)

    assert storage.list_recent_photo_paths() == [photo_path]
    storage.close()


def test_save_photo_reports_encoding_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = MediaStorage(project_root=tmp_path)
    frame = Frame(image=np.zeros((2, 2, 3), dtype=np.uint8))
    monkeypatch.setattr(cv2, "imencode", lambda *_args: (False, None))

    with pytest.raises(PhotoSaveError, match="Failed to encode photo"):
        storage.save_photo(frame)

    storage.close()

from pathlib import Path

import numpy as np

from capillaroscope_app.domain.models import Frame
from capillaroscope_app.storage.media_storage import MediaStorage


def test_list_recent_photo_paths_returns_saved_photo_path(tmp_path: Path) -> None:
    storage = MediaStorage(project_root=tmp_path)
    frame = Frame(image=np.zeros((2, 2, 3), dtype=np.uint8))

    photo_path = storage.save_photo(frame)

    assert storage.list_recent_photo_paths() == [photo_path]
    storage.close()

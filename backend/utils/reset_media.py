import os
import shutil
from pathlib import Path


def reset_media():
    """Delete all directories in media folder except '1' and '2'."""
    media_path = Path(__file__).parent / "media"

    if not media_path.exists():
        print(f"Media directory does not exist: {media_path}")
        return

    preserved_dirs = {"1", "2"}

    for item in media_path.iterdir():
        if item.is_dir() and item.name not in preserved_dirs:
            try:
                shutil.rmtree(item)
            except Exception as e:
                print(f"Error deleting {item.name}: {e}")

    for i in range(3, 5):
        os.makedirs(media_path / str(i), exist_ok=True)

    print("Media directory reset complete")


if __name__ == "__main__":
    reset_media()

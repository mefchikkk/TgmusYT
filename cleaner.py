import os
import shutil
from pathlib import Path

def cleanup_temp():
    temp_dir = Path("temp_audio")
    if temp_dir.exists():
        for file in temp_dir.glob("*"):
            try:
                if file.is_file():
                    file.unlink()
            except Exception as e:
                print(f"Ошибка при удалении {file}: {e}")

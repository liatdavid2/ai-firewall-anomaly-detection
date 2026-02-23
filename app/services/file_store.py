import json
import os
import threading
from typing import Dict, Any

_lock = threading.Lock()

def load_json(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        return {}
    with _lock:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

def save_json(file_path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with _lock:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

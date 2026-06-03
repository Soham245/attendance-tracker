"""Public surface for the recognition runtime.

Routes call into this service; the heavy lifting lives in
`app.recognition.runtime`. This file exists to keep the route -> service ->
runtime layering consistent with the rest of the backend.
"""
from typing import Any, Dict

from app.recognition import runtime


def start(app_state: Any) -> Dict[str, Any]:
    return runtime.start(app_state)


def stop(app_state: Any) -> Dict[str, Any]:
    return runtime.stop(app_state)


def get_status(app_state: Any) -> Dict[str, Any]:
    return runtime.get_status(app_state)

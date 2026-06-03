"""VisionAttend backend entry point.

Note on reload mode (``DEBUG=True``): uvicorn's file-watcher reloader
spawns a child process. On Windows, CTRL+C sends SIGINT to every
process in the console group, but the reloader's shutdown dance adds
latency and sometimes requires a second CTRL+C.  For production-like
behaviour (and cleaner shutdown), run with ``DEBUG=False`` or set
``ATTENDAI_NO_RELOAD=1``.
"""
import os
import uvicorn

from app.config.settings import settings


if __name__ == "__main__":
    # Allow disabling reload even in debug mode — useful when testing
    # shutdown behaviour or running CV runtimes that own the camera.
    no_reload = os.environ.get("ATTENDAI_NO_RELOAD", "0") == "1"
    use_reload = settings.DEBUG and not no_reload

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=use_reload,
    )

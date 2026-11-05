"""Startup script: checks Qdrant health, launches uvicorn."""

import sys
import httpx
from backend.config import settings


def check_qdrant():
    """Verify Qdrant is reachable before starting the server."""
    url = f"http://{settings.qdrant_host}:{settings.qdrant_port}/healthz"
    try:
        resp = httpx.get(url, timeout=5)
        if resp.status_code == 200:
            print(f"[OK] Qdrant is running at {settings.qdrant_host}:{settings.qdrant_port}")
            return True
    except httpx.ConnectError:
        pass

    print(
        f"[ERROR] Cannot reach Qdrant at {settings.qdrant_host}:{settings.qdrant_port}\n"
        "Start Qdrant first:\n"
        "  Docker:  docker run -d --name qdrant -p 6333:6333 qdrant/qdrant\n"
        "  Binary:  .\\qdrant.exe"
    )
    return False


def main():
    if not check_qdrant():
        sys.exit(1)

    import uvicorn

    print(f"Starting server at http://{settings.host}:{settings.port}")
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()

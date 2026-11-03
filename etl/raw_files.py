"""Raw landing-zone files and their provenance sidecars.

Every raw file written by an extractor gets a ``<name>.source.json`` next to
it recording where the data came from, so the load step can log the real
source URL instead of a local path.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_SIDECAR_SUFFIX = ".source.json"


def _sidecar_path(path: Path) -> Path:
    return path.with_name(path.name + _SIDECAR_SUFFIX)


def save_raw(output_dir: Path, filename: str, content: bytes, source_url: str) -> Path:
    """Write ``content`` unchanged and record ``source_url`` beside it."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_bytes(content)
    _sidecar_path(path).write_text(
        json.dumps(
            {
                "url": source_url,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )

    return path


def read_source_url(path: Path) -> str:
    """Return the URL a raw file was downloaded from.

    Falls back to the local path for files cached before sidecars existed.
    """
    sidecar = _sidecar_path(path)
    try:
        meta: object = json.loads(sidecar.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("%s has no %s; re-run Extract", path.name, sidecar.name)
        return str(path)
    if not isinstance(meta, dict) or not isinstance(meta.get("url"), str):
        raise ValueError(f"{sidecar}: expected an object with a 'url' string")

    return meta["url"]

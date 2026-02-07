import hashlib
import json
from pathlib import Path
from typing import Iterable


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_key(source: Path, options_key: str) -> str:
    stat = source.stat()
    raw = f"{source.resolve()}|{stat.st_size}|{int(stat.st_mtime_ns)}|{options_key}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def asset_cache_dir(proxy_root: Path, source: Path, options_key: str) -> Path:
    key = cache_key(source, options_key)
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in source.stem)
    return ensure_dir(proxy_root / f"{safe_name}_{key}")


def manifest_path(cache_dir: Path) -> Path:
    return cache_dir / "manifest.json"


def write_manifest(cache_dir: Path, source: Path, outputs: Iterable[Path]) -> None:
    data = {
        "source": str(source.resolve()),
        "outputs": [str(path.resolve()) for path in outputs],
    }
    manifest_path(cache_dir).write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")


def read_manifest(cache_dir: Path) -> list[Path]:
    manifest = manifest_path(cache_dir)
    if not manifest.exists():
        return []

    data = json.loads(manifest.read_text(encoding="utf-8"))
    paths = [Path(item) for item in data.get("outputs", [])]
    return [path for path in paths if path.exists()]


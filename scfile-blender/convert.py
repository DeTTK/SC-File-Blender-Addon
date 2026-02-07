from pathlib import Path
from typing import Iterable

from . import cache


MODEL_EXTENSIONS = {".mcsb", ".mcsa", ".mcvd"}
TEXTURE_EXTENSIONS = {".ol"}
IMAGE_EXTENSIONS = {".mic"}
TEXARR_EXTENSIONS = {".texarr"}


def options_signature(parse_skeleton: bool, parse_animation: bool, overwrite: bool) -> str:
    return f"skeleton={int(parse_skeleton)};animation={int(parse_animation)};overwrite={int(overwrite)}"


def expected_outputs(source: Path) -> list[str]:
    suffix = source.suffix.lower()
    if suffix in MODEL_EXTENSIONS:
        return [".glb"]
    if suffix in TEXTURE_EXTENSIONS:
        return [".dds"]
    if suffix in IMAGE_EXTENSIONS:
        return [".png"]
    if suffix in TEXARR_EXTENSIONS:
        return [".zip"]
    return []


def convert_to_proxy(
    source: Path,
    proxy_root: Path,
    parse_skeleton: bool,
    parse_animation: bool,
    overwrite: bool,
    keep_cache: bool,
) -> Iterable[Path]:
    from .bootstrap import setup_paths

    setup_paths()
    try:
        from scfile import UserOptions, convert
        from scfile.enums import FileFormat
    except Exception as err:
        raise RuntimeError(
            f"Failed to import bundled package 'scfile' ({err}). "
            "Most likely Python ABI mismatch in bundled dependencies."
        ) from err

    options_key = options_signature(parse_skeleton, parse_animation, overwrite)
    out_dir = cache.asset_cache_dir(proxy_root, source, options_key)

    if keep_cache:
        cached = cache.read_manifest(out_dir)
        if cached:
            return cached

    options = UserOptions(
        model_formats=(FileFormat.GLB,),
        parse_skeleton=parse_skeleton,
        parse_animation=parse_animation,
        overwrite=overwrite,
    )
    convert.auto(source=source, output=out_dir, options=options)

    output_paths = []
    for suffix in expected_outputs(source):
        path = out_dir / f"{source.stem}{suffix}"
        if path.exists():
            output_paths.append(path)

    cache.write_manifest(out_dir, source, output_paths)
    return output_paths

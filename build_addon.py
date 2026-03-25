from __future__ import annotations

from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parent
ADDON_ROOT = ROOT / "scfile-blender"
DIST_DIR = ROOT / "dist"
REQ_FILE = ROOT / "requirements-vendor.txt"
SOURCE_SCFILE_DIR = ROOT / "scfile"
SOURCE_SCFILE_EGG = ROOT / "sc_file.egg-info"


def clean_vendor(vendor_dir: Path) -> None:
    if vendor_dir.exists():
        shutil.rmtree(vendor_dir)
    vendor_dir.mkdir(parents=True, exist_ok=True)


def copy_scfile(vendor_dir: Path) -> None:
    if not SOURCE_SCFILE_DIR.exists():
        raise FileNotFoundError(f"Missing source package directory: {SOURCE_SCFILE_DIR}")

    shutil.copytree(SOURCE_SCFILE_DIR, vendor_dir / "scfile")

    if SOURCE_SCFILE_EGG.exists():
        shutil.copytree(SOURCE_SCFILE_EGG, vendor_dir / "sc_file.egg-info")


def install_vendor_requirements(
    vendor_dir: Path,
    pip_python: str,
    target_python: str | None,
    target_abi: str | None,
    target_platform: str | None,
) -> None:
    if target_python is None or target_abi is None or target_platform is None:
        detected_python, detected_abi, detected_platform = detect_target_tags(pip_python)
        if target_python is None:
            target_python = detected_python
        if target_abi is None:
            target_abi = detected_abi
        if target_platform is None:
            target_platform = detected_platform

    cmd = [
        pip_python,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--target",
        str(vendor_dir),
        "--platform",
        target_platform,
        "--implementation",
        "cp",
        "--python-version",
        target_python,
        "--abi",
        target_abi,
        "--only-binary",
        ":all:",
        "-r",
        str(REQ_FILE),
    ]
    subprocess.run(cmd, check=True)


def detect_target_tags(pip_python: str) -> tuple[str, str, str]:
    script = (
        "import json, sys, sysconfig;"
        "platform = sysconfig.get_platform().replace('-', '_').replace('.', '_');"
        "print(json.dumps({'python': f'{sys.version_info[0]}.{sys.version_info[1]}', "
        "'abi': f'cp{sys.version_info[0]}{sys.version_info[1]}', "
        "'platform': platform}))"
    )
    out = subprocess.check_output([pip_python, "-c", script], text=True)
    data = json.loads(out)
    return data["python"], data["abi"], data["platform"]


def build_zip(zip_name: str) -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DIST_DIR / zip_name
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in ADDON_ROOT.rglob("*"):
            if not _should_package(path):
                continue
            arcname = path.relative_to(ADDON_ROOT.parent).as_posix()
            zf.write(path, arcname=arcname)

    return zip_path


def _should_package(path: Path) -> bool:
    if path.is_dir():
        return False

    parts = set(path.parts)
    name = path.name.lower()

    if "__pycache__" in parts:
        return False
    if name.endswith((".pyc", ".pyo")):
        return False

    # Skip test data from vendored dependencies to keep release zip smaller.
    if "tests" in parts or "testing" in parts:
        return False

    # CLI entry points from wheels are not needed inside Blender addon package.
    if "vendor" in parts and "bin" in parts:
        return False

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Build standalone Blender addon with vendored dependencies")
    parser.add_argument("--zip-name", default="scfile_blender_addon.zip")
    parser.add_argument(
        "--skip-pip",
        action="store_true",
        help="Do not run pip install for vendor dependencies",
    )
    parser.add_argument(
        "--pip-python",
        default=sys.executable,
        help="Python executable used for pip install (use Blender's Python for ABI compatibility)",
    )
    parser.add_argument(
        "--target-python",
        default=None,
        help="Target Python version for binary wheels, example: 3.13 (default: detect from --pip-python)",
    )
    parser.add_argument(
        "--target-abi",
        default=None,
        help="Target CPython ABI tag, example: cp313 (default: detect from --pip-python)",
    )
    parser.add_argument(
        "--target-platform",
        default=None,
        help="Target platform tag for wheels, example: win_amd64 (default: detect from --pip-python)",
    )
    args = parser.parse_args()

    vendor_dir = ADDON_ROOT / "vendor"
    target_python = args.target_python
    target_abi = args.target_abi
    target_platform = args.target_platform
    if target_python is None or target_abi is None or target_platform is None:
        target_python, target_abi, target_platform = detect_target_tags(args.pip_python)

    clean_vendor(vendor_dir)
    copy_scfile(vendor_dir)

    if not args.skip_pip:
        install_vendor_requirements(
            vendor_dir=vendor_dir,
            pip_python=args.pip_python,
            target_python=target_python,
            target_abi=target_abi,
            target_platform=target_platform,
        )

    zip_path = build_zip(args.zip_name)
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Built addon: {zip_path}")
    print(f"Zip size: {zip_size_mb:.2f} MB")
    print(f"Pip Python: {args.pip_python}")
    print(
        "Wheel target: "
        f"python={target_python}, abi={target_abi}, platform={target_platform}"
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path
import argparse
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parent.parent
ADDON_ROOT = ROOT / "blender_addon" / "scfile_blender"
DIST_DIR = ROOT / "blender_addon" / "dist"
REQ_FILE = ROOT / "blender_addon" / "requirements-vendor.txt"
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
    target_python: str,
    target_abi: str,
    target_platform: str,
) -> None:
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
        default="3.11",
        help="Target Python version for binary wheels, example: 3.11",
    )
    parser.add_argument(
        "--target-abi",
        default="cp311",
        help="Target CPython ABI tag, example: cp311",
    )
    parser.add_argument(
        "--target-platform",
        default="win_amd64",
        help="Target platform tag for wheels, example: win_amd64",
    )
    args = parser.parse_args()

    vendor_dir = ADDON_ROOT / "vendor"

    clean_vendor(vendor_dir)
    copy_scfile(vendor_dir)

    if not args.skip_pip:
        install_vendor_requirements(
            vendor_dir=vendor_dir,
            pip_python=args.pip_python,
            target_python=args.target_python,
            target_abi=args.target_abi,
            target_platform=args.target_platform,
        )

    zip_path = build_zip(args.zip_name)
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Built addon: {zip_path}")
    print(f"Zip size: {zip_size_mb:.2f} MB")
    print(f"Pip Python: {args.pip_python}")
    print(
        "Wheel target: "
        f"python={args.target_python}, abi={args.target_abi}, platform={args.target_platform}"
    )


if __name__ == "__main__":
    main()

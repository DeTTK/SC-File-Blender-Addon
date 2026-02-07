from pathlib import Path
import site
import sys


def setup_paths() -> None:
    addon_dir = Path(__file__).resolve().parent
    vendor_dir = addon_dir / "vendor"
    if not vendor_dir.exists():
        return

    vendor_str = str(vendor_dir)
    if vendor_str not in sys.path:
        sys.path.insert(0, vendor_str)

    site.addsitedir(vendor_str)


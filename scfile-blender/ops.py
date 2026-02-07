from pathlib import Path
import shutil
import zipfile

import bpy
from bpy.props import CollectionProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from . import convert, prefs


SUPPORTED_EXTENSIONS = ".mcsb;.mcsa;.mcvd;.ol;.mic;.texarr"


class SCFILE_OT_clean_proxy(bpy.types.Operator):
    bl_idname = "scfile.clean_proxy"
    bl_label = "Clean Proxy Cache"
    bl_description = "Delete converted files from proxy directory"

    def invoke(self, context, _event):
        return context.window_manager.invoke_confirm(self, _event)

    def execute(self, context):
        addon_prefs = prefs.get_prefs(context)
        proxy_root = Path(bpy.path.abspath(addon_prefs.proxy_dir)).expanduser()

        if not proxy_root.exists():
            self.report({"INFO"}, "Proxy directory does not exist")
            return {"FINISHED"}

        removed = 0
        for child in proxy_root.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                removed += 1
            except Exception as err:
                self.report({"WARNING"}, f"Failed to delete '{child.name}': {err}")

        self.report({"INFO"}, f"Removed {removed} proxy entries")
        return {"FINISHED"}


def _collect_sources(filepath: str, directory: str, files) -> list[Path]:
    base_dir = Path(directory) if directory else Path(filepath).parent
    if files:
        return [base_dir / f.name for f in files]
    if filepath:
        return [Path(filepath)]
    return []


def _run_import(context, filepath: str, directory: str, files) -> tuple[int, int]:
    addon_prefs = prefs.get_prefs(context)
    proxy_root = Path(bpy.path.abspath(addon_prefs.proxy_dir)).expanduser()
    proxy_root.mkdir(parents=True, exist_ok=True)

    sources = _collect_sources(filepath, directory, files)
    imported = 0
    warnings = 0

    for src in sources:
        src = src.resolve()
        try:
            outputs = convert.convert_to_proxy(
                source=src,
                proxy_root=proxy_root,
                parse_skeleton=addon_prefs.parse_skeleton,
                parse_animation=addon_prefs.parse_animation,
                overwrite=addon_prefs.overwrite_proxy,
                keep_cache=addon_prefs.keep_proxy,
            )
        except Exception as err:
            print(f"[SCFILE][ERROR] Failed to convert '{src.name}': {err}")
            continue

        for out_path in outputs:
            try:
                if out_path.suffix.lower() == ".glb":
                    bpy.ops.import_scene.gltf(filepath=str(out_path))
                    imported += 1
                elif out_path.suffix.lower() in {".png", ".dds"}:
                    bpy.data.images.load(str(out_path), check_existing=True)
                    imported += 1
                elif out_path.suffix.lower() == ".zip":
                    extracted = _extract_zip(out_path)
                    imported += _load_images(extracted)
                else:
                    warnings += 1
                    print(f"[SCFILE][WARN] Unsupported proxy output: {out_path.name}")
            except Exception as err:
                warnings += 1
                print(f"[SCFILE][WARN] Failed to import '{out_path.name}': {err}")

    print(f"[SCFILE][INFO] Imported={imported} warnings={warnings}")
    return imported, warnings


def _extract_zip(zip_path: Path) -> list[Path]:
    extract_dir = zip_path.with_suffix("")
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, mode="r") as zf:
        zf.extractall(extract_dir)

    return [p for p in extract_dir.rglob("*") if p.is_file()]


def _load_images(files: list[Path]) -> int:
    loaded = 0
    for path in files:
        if path.suffix.lower() not in {".png", ".dds"}:
            continue
        try:
            bpy.data.images.load(str(path), check_existing=True)
            loaded += 1
        except RuntimeError:
            continue
    return loaded


class SCFILE_OT_import_assets_dialog(bpy.types.Operator, ImportHelper):
    bl_idname = "scfile.import_assets_dialog"
    bl_label = "Import SC Assets"
    bl_options = {"UNDO"}

    filename_ext = ""
    filter_glob: StringProperty(default="*.mcsb;*.mcsa;*.mcvd;*.ol;*.mic;*.texarr", options={"HIDDEN"})
    files: CollectionProperty(type=bpy.types.OperatorFileListElement, options={"HIDDEN", "SKIP_SAVE"})
    directory: StringProperty(subtype="DIR_PATH", options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        _run_import(context, self.filepath, self.directory, self.files)
        return {"FINISHED"}


class SCFILE_OT_import_assets_drop(bpy.types.Operator):
    bl_idname = "scfile.import_assets_drop"
    bl_label = "Import SC Assets (Drop)"
    bl_options = {"UNDO"}

    filepath: StringProperty(subtype="FILE_PATH", options={"HIDDEN", "SKIP_SAVE"})
    files: CollectionProperty(type=bpy.types.OperatorFileListElement, options={"HIDDEN", "SKIP_SAVE"})
    directory: StringProperty(subtype="DIR_PATH", options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        _run_import(context, self.filepath, self.directory, self.files)
        return {"FINISHED"}


class SCFILE_FH_drag_drop(bpy.types.FileHandler):
    bl_idname = "SCFILE_FH_drag_drop_exec_v2"
    bl_label = "SC File Drag and Drop"
    bl_import_operator = SCFILE_OT_import_assets_drop.bl_idname
    bl_file_extensions = SUPPORTED_EXTENSIONS

    @classmethod
    def poll_drop(cls, context):
        return context.area and context.area.type in {"VIEW_3D", "OUTLINER", "IMAGE_EDITOR"}

from pathlib import Path

import bpy
from bpy.props import BoolProperty, StringProperty


def _default_proxy_dir() -> str:
    return str(Path.home() / "scfile_proxy")


class SCFILE_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    proxy_dir: StringProperty(
        name="Proxy Directory",
        subtype="DIR_PATH",
        default=_default_proxy_dir(),
        description="Directory where converted proxy assets are stored",
    )
    overwrite_proxy: BoolProperty(
        name="Overwrite Converted Files",
        default=True,
        description="Overwrite converted cache files if they already exist",
    )
    parse_skeleton: BoolProperty(
        name="Parse Skeleton",
        default=True,
        description="Export skeleton when converting models",
    )
    parse_animation: BoolProperty(
        name="Parse Animation",
        default=False,
        description="Export builtin clips when converting models (GLB only)",
    )
    keep_proxy: BoolProperty(
        name="Keep Proxy Cache",
        default=True,
        description="Keep converted files in proxy directory for reuse",
    )

    def draw(self, _context):
        layout = self.layout
        layout.prop(self, "proxy_dir")
        layout.prop(self, "overwrite_proxy")
        layout.prop(self, "parse_skeleton")
        layout.prop(self, "parse_animation")
        layout.prop(self, "keep_proxy")
        layout.separator()
        layout.operator("scfile.clean_proxy", icon="TRASH")


def get_prefs(context) -> SCFILE_AddonPreferences:
    addon = context.preferences.addons.get(__package__)
    if addon and addon.preferences:
        return addon.preferences
    raise RuntimeError("SC File Importer preferences are unavailable")

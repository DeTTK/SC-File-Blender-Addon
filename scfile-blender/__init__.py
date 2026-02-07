bl_info = {
    "name": "SC-File Blender Addon",
    "author": "TeamDima",
    "version": (0, 2, 0),
    "blender": (4, 0, 0),
    "location": "File > Import / Drag and Drop",
    "description": "Импорт ассетов из STALCRAFT в Blender",
    "category": "Import-Export",
}

from .bootstrap import setup_paths

setup_paths()

from . import ops, prefs


CLASSES = (
    prefs.SCFILE_AddonPreferences,
    ops.SCFILE_OT_clean_proxy,
    ops.SCFILE_OT_import_assets_dialog,
    ops.SCFILE_OT_import_assets_drop,
    ops.SCFILE_FH_drag_drop,
)


def menu_func_import(self, _context):
    self.layout.operator(
        ops.SCFILE_OT_import_assets_dialog.bl_idname,
        text="SC-File Assets (.mcsb/.mcsa/.ol/.mic/.texarr)",
    )


def register():
    import bpy

    for cls in CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    import bpy

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

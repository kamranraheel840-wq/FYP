# -*- mode: python ; coding: utf-8 -*-
import os
import sys

from PyInstaller.utils.hooks import collect_all

root = SPECPATH
ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")
compat_runtime = os.path.join(sys.base_prefix, "abi3t-compat", "python3t.dll")
if os.path.isfile(compat_runtime):
    ctk_binaries.append((compat_runtime, "."))
datas = list(ctk_datas)
for filename in (
    "face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx",
):
    model_path = os.path.join(root, "models", filename)
    if os.path.isfile(model_path):
        datas.append((model_path, "models"))

# Application icon, used for the EXE and for window title bars.
for filename in ("icon.ico", "icon.png"):
    asset_path = os.path.join(root, "assets", filename)
    if os.path.isfile(asset_path):
        datas.append((asset_path, "assets"))

icon_path = os.path.join(root, "assets", "icon.ico")

a = Analysis(
    [os.path.join(root, "police_system_IT.py")],
    pathex=[root],
    binaries=ctk_binaries,
    datas=datas,
    hiddenimports=ctk_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CriminalRecordManagementSystem",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=icon_path if os.path.isfile(icon_path) else None,
)

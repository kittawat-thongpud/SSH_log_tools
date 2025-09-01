# -*- mode: python ; coding: utf-8 -*-

import os, sys, shutil
from pathlib import Path
from PyInstaller.building.build_main import Analysis, PYZ, EXE
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

APP_NAME = "SSH_Log_Tools"
ENTRY    = "main.py"
ICON     = "icon.ico"            # build-time exe icon filename

PROJECT_ROOT = Path(SPECPATH)    # safer than os.getcwd()
DIST_ROOT    = Path(DISTPATH)    # respects --distpath

# ---------- Hidden imports ----------
hidden = []
hidden += collect_submodules("flask")
hidden += collect_submodules("jinja2")
hidden += collect_submodules("werkzeug")
hidden += collect_submodules("pystray")
hidden += collect_submodules("PIL")
hidden += collect_submodules("paramiko")
hidden += collect_submodules("cryptography")
hidden += collect_submodules("openpyxl")
hidden += collect_submodules("xlsxwriter")
hidden += collect_submodules("olefile")
hidden += ["ctypes"]  # defensive

# ---------- Data files (bundle templates/static and icon.ico) ----------
# These will be available at runtime via sys._MEIPASS (resource_path).
datas = collect_data_files("app", includes=["templates/*", "static/*"])
icon_src = PROJECT_ROOT / ICON
if icon_src.exists():
    # make icon.ico available inside the onefile bundle, too
    datas.append((str(icon_src), "."))

# ---------- Pick up ffi/vcruntime so _ctypes works ----------
binaries = []
datas = collect_data_files("app", includes=["templates/*", "static/*"])

def add_bins(root: Path, patterns: list[str]):
    if not root or not root.exists():
        return
    for pat in patterns:
        for p in root.glob(pat):
            binaries.append((str(p), "."))

# venv/base DLLs
VENV_DLLS = Path(sys.prefix) / "DLLs"
BASE_DLLS = Path(sys.base_prefix) / "DLLs"
add_bins(VENV_DLLS, ["libffi-*.dll", "ffi-*.dll", "libffi.dll", "ffi.dll"])
add_bins(BASE_DLLS, ["libffi-*.dll", "ffi-*.dll", "libffi.dll", "ffi.dll"])
add_bins(Path(sys.prefix),      ["vcruntime140*.dll", "vcruntime*.dll"])
add_bins(Path(sys.base_prefix), ["vcruntime140*.dll", "vcruntime*.dll"])

# ---------- Build graph ----------
a = Analysis(
    [str(PROJECT_ROOT / ENTRY)],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
<<<<<<< ours
    datas=datas,              # bundle templates/static and icon.ico
=======
    datas=datas,              # bundle templates/static; keep config/icon external
>>>>>>> theirs
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                 # set False if UPX causes issues
    upx_exclude=[],
    runtime_tmpdir=None,      # onefile
    console=False,
    icon=[str(icon_src)] if icon_src.exists() else None,
)

# ---------- Also copy external files next to EXE (onefile) ----------
# This gives you editable config and an external icon beside the .exe as well.
for fname in ("config.json", ICON):
    src = PROJECT_ROOT / fname
    if src.exists():
        try:
            shutil.copy2(src, DIST_ROOT / src.name)
            print(f"[spec] Copied {src} -> {DIST_ROOT}")
        except Exception as e:
            print(f"[spec] Copy failed for {src}: {e}")
    else:
        print(f"[spec] Info: {fname} not found at build time")

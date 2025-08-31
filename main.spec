# -*- mode: python ; coding: utf-8 -*-

import os, sys, glob, shutil
from pathlib import Path
from PyInstaller.building.build_main import Analysis, PYZ, EXE
from PyInstaller.utils.hooks import collect_submodules

APP_NAME = "SSH_Log_Tools"
ENTRY    = "main.py"
ICON     = "ssh_tools_record.ico"

BASE = Path(os.getcwd())
DIST = BASE / "dist"

# ---------- Hidden imports for your stack ----------
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

# ---------- Find libffi & MSVC runtime from Anaconda/venv ----------
binaries = []

def add_bins(root: Path, patterns: list[str]):
    if not root or not root.exists():
        return
    for pat in patterns:
        for p in root.glob(pat):
            binaries.append((str(p), "."))

# venv / base DLLs locations
VENV_DLLS  = Path(sys.prefix) / "DLLs"
BASE_DLLS  = Path(sys.base_prefix) / "DLLs"

# Anaconda layout (if env var exists)
CONDA_LIBBIN = None
cp = os.environ.get("CONDA_PREFIX")
if cp:
    cand = Path(cp) / "Library" / "bin"
    if cand.exists():
        CONDA_LIBBIN = cand

# Collect libffi variants (names vary)
ffi_patterns = ["libffi-*.dll", "ffi-*.dll", "libffi.dll", "ffi.dll"]
add_bins(VENV_DLLS, ffi_patterns)
add_bins(BASE_DLLS, ffi_patterns)
if CONDA_LIBBIN:
    add_bins(CONDA_LIBBIN, ffi_patterns)

# Add MSVC runtime (defensive)
# vcruntime may sit in the env root
add_bins(Path(sys.prefix),  ["vcruntime140*.dll", "vcruntime*.dll"])
add_bins(Path(sys.base_prefix), ["vcruntime140*.dll", "vcruntime*.dll"])

# ---------- Build graph ----------
a = Analysis(
    [ENTRY],
    pathex=[str(BASE)],
    binaries=binaries,   # <- include ffi/vcruntime so _ctypes loads
    datas=[],            # keep config/icon external at runtime
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
    upx=True,            # set False if you hit UPX issues
    upx_exclude=[],
    runtime_tmpdir=None, # one-file
    console=False,
    icon=[ICON] if (BASE / ICON).exists() else None,
)

# ---------- Copy external runtime files next to the EXE ----------
try:
    DIST.mkdir(exist_ok=True)
    for fname in ("config.json", ICON):
        src = BASE / fname
        if src.exists():
            shutil.copy2(src, DIST / src.name)
            print(f"[spec] Copied {src} -> {DIST}")
        else:
            print(f"[spec] Info: {fname} not found at build time")
except Exception as e:
    print(f"[spec] Copy step warning: {e}")

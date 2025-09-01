# -*- mode: python ; coding: utf-8 -*-

import os, sys, shutil
from pathlib import Path
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
from PyInstaller.building.datastruct import Tree  # ✅ ใช้ได้ แต่ห้ามใส่ใน datas= ของ Analysis

APP_NAME = "SSH_Log_Tools"
ENTRY    = "main.py"
ICON     = "icon.ico"

PROJECT_ROOT = Path(SPECPATH)
DIST_ROOT    = Path(DISTPATH)

BUILD_MODE = "onedir"   # "onefile" ก็ได้

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
hidden += ["ctypes"]

# ---------- Data files (เฉพาะคู่ (src, dest) เท่านั้น) ----------
datas = []
# ถ้า app เป็นแพ็กเกจ (มี __init__.py) วิธีนี้ใช้ได้
datas += collect_data_files("app", includes=["templates/**", "static/**"])

# ฝังไฟล์โคน (สองค่าต่อ tuple)
for fname in ("config.json", "icon.ico"):
    f = PROJECT_ROOT / fname
    if f.exists():
        datas.append((str(f), "."))

icon_src = PROJECT_ROOT / ICON

# ---------- Binaries ----------
binaries = []
def add_bins(root: Path, patterns: list[str]):
    if not root or not root.exists():
        return
    for pat in patterns:
        for p in root.glob(pat):
            binaries.append((str(p), "."))

add_bins(Path(sys.prefix) / "DLLs", ["libffi*.dll", "ffi*.dll"])
add_bins(Path(sys.base_prefix) / "DLLs", ["libffi*.dll", "ffi*.dll"])
add_bins(Path(sys.prefix),      ["vcruntime140*.dll", "vcruntime*.dll"])
add_bins(Path(sys.base_prefix), ["vcruntime140*.dll", "vcruntime*.dll"])

# ---------- Build Graph ----------
a = Analysis(
    [str(PROJECT_ROOT / ENTRY)],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,                 # ❗ ที่นี่ต้องมีเฉพาะ (src, dest) pairs
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# ✅ ตอนนี้ค่อย “แทรก” โฟลเดอร์แบบ Tree เข้าไปใน a.datas (ไม่ใช่ใน datas=)
tpl_dir = PROJECT_ROOT / "app" / "templates"
sta_dir = PROJECT_ROOT / "app" / "static"
if tpl_dir.exists():
    a.datas += Tree(str(tpl_dir), prefix="app/templates")
if sta_dir.exists():
    a.datas += Tree(str(sta_dir), prefix="app/static")

pyz = PYZ(a.pure, a.zipped_data)

if BUILD_MODE == "onefile":
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
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        icon=[str(icon_src)] if icon_src.exists() else None,
    )
    build_target = exe
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        icon=[str(icon_src)] if icon_src.exists() else None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=APP_NAME,
    )
    build_target = coll

# ---------- post-copy helper ----------
def _copy_to_dist(src: Path):
    dist_root = Path(DISTPATH) / APP_NAME
    if not src.exists():
        return
    try:
        if src.is_dir():
            shutil.copytree(src, dist_root / src.name, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dist_root / src.name)
        print(f"[spec] Copied {src} -> {dist_root}")
    except Exception as e:
        print(f"[spec] Copy failed for {src}: {e}")

# วางไฟล์แก้ไขง่ายข้าง exe/folder เพิ่มได้ตามต้องการ
_copy_to_dist(PROJECT_ROOT / "config.json")
_copy_to_dist(PROJECT_ROOT / "icon.ico")

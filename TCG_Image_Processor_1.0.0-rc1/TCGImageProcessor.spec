# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_dir = Path(SPECPATH)

datas = [
    (str(project_dir / "config.json"), "."),
    (str(project_dir / "stats.json"), "."),
    (str(project_dir / "history.json"), "."),
    (str(project_dir / "README.md"), "."),
    (str(project_dir / "CHANGELOG.md"), "."),
    (str(project_dir / "ROADMAP.md"), "."),
]

icon_path = project_dir / "assets" / "app.ico"
icon_value = str(icon_path) if icon_path.exists() else None

a = Analysis(
    ["main.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PIL._tkinter_finder",
        "cv2",
        "numpy",
        "watchdog.observers.winapi",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TCG Image Processor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_value,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TCG Image Processor",
)

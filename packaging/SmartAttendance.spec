"""Windows x64 one-folder application; paths are relative to this spec."""
from pathlib import Path
import struct
import sys

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

if sys.platform != "win32" or struct.calcsize("P") != 8:
    raise RuntimeError("Build with the Windows x64 .venv-build interpreter.")

project_root = Path(SPECPATH).resolve().parent
model_root = project_root / "assets" / "models"
model_files = (
    "face_detection_yunet_2026may.onnx",
    "face_recognition_sface_2021dec.onnx",
    "LICENSE-SFace.txt",
    "LICENSE-YuNet.txt",
    "SOURCES.md",
)

# Keep package-relative font paths. Normal hooks collect Qt and QtAwesome data.
datas = collect_data_files("attendance_app", includes=["assets/fonts/*.ttf"])
datas += [(str(model_root / name), "assets/models") for name in model_files]
datas += copy_metadata("smart-attendance")

a = Analysis(
    [str(project_root / "src" / "attendance_app" / "main.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    name="SmartAttendance",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    contents_directory="_internal",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="SmartAttendance",
)

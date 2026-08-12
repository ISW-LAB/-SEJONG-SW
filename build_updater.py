# -*- coding: utf-8 -*-
"""
updater_app.py → 수종데이터업데이터.exe 빌드 스크립트 (자체 완결형).

탄소저장량측정모듈의 **전체 소스(carbon_calculator + main.py + build_exe.py 등)를
updater.exe 내부에 번들**한다. 따라서 빌드된 수종데이터업데이터.exe 는 소스 폴더 없이
단독으로 배포·실행할 수 있으며, 사용자는 통합 species_data.json 만 넣으면 새
탄소저장량측정모듈.exe 를 빌드할 수 있다.

사용법:
    python build_updater.py              # onefile (기본)
    python build_updater.py --onedir     # 폴더형
    python build_updater.py --debug      # 콘솔창 표시
    python build_updater.py --upx        # UPX 압축
    python build_updater.py --clean-cache
    python build_updater.py --rebuild-venv

배포 방법:
    빌드된 수종데이터업데이터.exe 하나만 배포하면 된다.
    사용자 PC 에 Python 3.10+ 이 있으면 이 exe 로 재빌드까지 가능하고,
    Python 이 없어도 'JSON 적용' 모드로 기존 exe 옆에 데이터만 갱신할 수 있다.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import venv as _venv_mod
from pathlib import Path


HERE       = Path(__file__).resolve().parent
ENTRY      = HERE / "updater_app.py"
APP_NAME   = "수종데이터업데이터"
REQ_FILE   = HERE / "requirements.txt"
BUILD_VENV = Path.home() / ".carboncalc_build_venv"
_OLD_VENV  = HERE / ".build_venv"

# ── 플랫폼별 venv 레이아웃 / 실행파일 확장자 ──────────────────────────────
_VENV_BIN = "Scripts" if os.name == "nt" else "bin"
_EXE_EXT  = ".exe" if os.name == "nt" else ""


def _venv_python(venv: Path) -> Path:
    return venv / _VENV_BIN / f"python{_EXE_EXT}"


def _venv_ready(python: Path) -> bool:
    """venv 에 PyInstaller + PyQt5 가 설치되어 재사용 가능한지 확인."""
    if not python.exists():
        return False
    r = subprocess.run(
        [str(python), "-c", "import PyInstaller, PyQt5"],
        capture_output=True,
    )
    return r.returncode == 0

# ── updater.exe 내부에 번들할 소스 (탄소저장량측정모듈 전체 코드 로직) ──────────
# 런타임에 _MEIPASS/bundled_src 로 풀려, updater 가 이를 임시 작업폴더로 복사해 빌드한다.
_BUNDLE_ROOT_FILES = (
    "main.py",
    "build_exe.py", "requirements.txt",
    "species_data.json",             # 기본 통합 데이터 (사용자 JSON 이 덮어씀)
)
_CC_DIR = HERE / "carbon_calculator"

_ICON_CANDIDATES = (
    HERE / "icon.ico",
    HERE.parent / "previous_application" / "icon.ico",
)


def find_icon() -> Path | None:
    for p in _ICON_CANDIDATES:
        if p.exists():
            return p
    return None


def collect_bundled_datas() -> list[tuple[str, str]]:
    """탄소저장량측정모듈 소스를 PyInstaller datas 형식 (src, dest) 로 수집.

    dest 'bundled_src' 는 런타임에 _MEIPASS/bundled_src 로 풀린다.
    """
    datas: list[tuple[str, str]] = []
    for fn in _BUNDLE_ROOT_FILES:
        p = HERE / fn
        if p.exists():
            datas.append((str(p), "bundled_src"))
        else:
            print(f"[경고] 번들 대상 누락: {p}")

    icon = find_icon()
    if icon:
        datas.append((str(icon), "bundled_src"))

    if not _CC_DIR.exists():
        sys.exit(f"[오류] carbon_calculator 패키지를 찾을 수 없습니다: {_CC_DIR}")
    for py in sorted(_CC_DIR.glob("*.py")):
        datas.append((str(py), "bundled_src/carbon_calculator"))

    return datas


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build 수종데이터업데이터.exe")
    p.add_argument("--onedir",        action="store_true", help="폴더 형태로 빌드.")
    p.add_argument("--debug",         action="store_true", help="콘솔창 표시.")
    p.add_argument("--upx",           action="store_true", help="UPX 압축 활성화.")
    p.add_argument("--clean-cache",   action="store_true", help="build/, dist/ 삭제.")
    p.add_argument("--rebuild-venv",  action="store_true", help="빌드 venv 강제 재생성.")
    return p.parse_args()


def clean_build_artifacts() -> None:
    for name in ("build", "dist"):
        path = HERE / name
        if path.exists():
            print(f"[정리] {path}")
            shutil.rmtree(path, ignore_errors=True)


def ensure_build_venv(rebuild: bool = False) -> Path:
    """PyQt5 + PyInstaller 가 설치된 빌드 전용 venv 를 준비한다.

    build_exe.py 의 빌드 venv 와 동일한 위치를 공유한다.
    requirements.txt(PyQt5 포함)가 이미 설치돼 있으면 재사용한다.
    """
    python = _venv_python(BUILD_VENV)

    if _OLD_VENV.exists():
        print(f"[환경] 이전 빌드 venv 삭제: {_OLD_VENV}")
        shutil.rmtree(_OLD_VENV, ignore_errors=True)

    if rebuild and BUILD_VENV.exists():
        print(f"[환경] 기존 빌드 venv 삭제: {BUILD_VENV}")
        shutil.rmtree(BUILD_VENV, ignore_errors=True)

    if not python.exists():
        print(f"[환경] 빌드 전용 가상환경 생성 중 (최초 1회, 몇 분 소요)...")
        print(f"       위치: {BUILD_VENV}")
        _venv_mod.create(str(BUILD_VENV), with_pip=True, clear=False)

    if not python.exists():
        sys.exit(f"[오류] 빌드 venv Python 생성에 실패했습니다: {python}")

    # pip 보장 (일부 배포판은 ensurepip 필요)
    subprocess.run(
        [str(python), "-m", "ensurepip", "--upgrade"],
        capture_output=True,
    )

    if _venv_ready(python):
        print(f"[환경] 기존 빌드 venv 재사용: {BUILD_VENV}")
        return BUILD_VENV

    print("[환경] pip 업그레이드 중...")
    subprocess.run(
        [str(python), "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
        check=True,
    )
    if REQ_FILE.exists():
        print(f"[환경] requirements.txt 패키지 설치 중...")
        subprocess.run(
            [str(python), "-m", "pip", "install", "--quiet", "-r", str(REQ_FILE)],
            check=True,
        )
    else:
        print("[환경] PyQt5 설치 중...")
        subprocess.run(
            [str(python), "-m", "pip", "install", "--quiet", "PyQt5"],
            check=True,
        )
    print("[환경] PyInstaller 설치 중...")
    subprocess.run(
        [str(python), "-m", "pip", "install", "--quiet", "pyinstaller"],
        check=True,
    )
    print("[환경] 빌드 환경 준비 완료.")
    return BUILD_VENV


# ─────────────────────────── spec 파일 ───────────────────────────

# updater는 PyQt5 + 표준 라이브러리만 사용. matplotlib/openpyxl/PIL 등 불필요.
_SPEC_ANALYSIS = r"""# -*- mode: python ; coding: utf-8 -*-
# Auto-generated by build_updater.py — do not edit manually.

import os
from PyInstaller.utils.hooks import collect_dynamic_libs

block_cipher = None

_EXCL_DLL = {
    'opengl32sw.dll', 'd3dcompiler_47.dll',
    'libglesv2.dll', 'libegl.dll',
    'qt5quick.dll', 'qt5qml.dll', 'qt5qmlmodels.dll', 'qt5qmlworkerscript.dll',
    'qt5designer.dll', 'qt5xmlpatterns.dll',
    'qt5location.dll', 'qt5multimedia.dll', 'qt5multimediaquick.dll',
    'qt5sql.dll', 'qt5bluetooth.dll',
    'qt5quick3d.dll', 'qt5quick3druntimerender.dll',
    'qt5quick3dassetimporter.dll', 'qt5quick3dutils.dll',
}
_EXCL_DIR = {
    'qml', 'sqldrivers', 'assetimporters', 'geoservices',
    'geometryloaders', 'sceneparsers', 'renderers', 'playlistformats',
}

def _keep_bin(src):
    if os.path.basename(src).lower() in _EXCL_DLL:
        return False
    parts = src.replace(os.sep, '/').lower().split('/')
    return not any(p in _EXCL_DIR for p in parts)

_qt5_binaries = [
    (src, dest) for src, dest in collect_dynamic_libs('PyQt5')
    if _keep_bin(src)
]

a = Analysis(
    [__ENTRY__],
    pathex=[__HERE__],
    binaries=_qt5_binaries,
    datas=__DATAS__,
    hiddenimports=['PyQt5.sip'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib', 'numpy', 'openpyxl', 'PIL', 'pandas',
        'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineCore',
        'PyQt5.QtQuick', 'PyQt5.QtQml', 'PyQt5.QtQuickWidgets',
        'PyQt5.QtQuick3D', 'PyQt5.QtQuickControls2',
        'PyQt5.QtDesigner',
        'PyQt5.QtMultimedia', 'PyQt5.QtMultimediaWidgets',
        'PyQt5.QtLocation', 'PyQt5.QtPositioning',
        'PyQt5.QtNetwork', 'PyQt5.QtNetworkAuth', 'PyQt5.QtSql',
        'PyQt5.Qt3DCore', 'PyQt5.Qt3DRender', 'PyQt5.Qt3DInput',
        'PyQt5.Qt3DLogic', 'PyQt5.Qt3DAnimation', 'PyQt5.Qt3DExtras',
        'PyQt5.QtBluetooth', 'PyQt5.QtXmlPatterns',
        'PySide2', 'PySide6', 'PyQt6',
        'torch', 'torchvision', 'torchaudio',
        'cv2', 'scipy', 'numba', 'llvmlite',
        'tensorflow', 'keras', 'sklearn', 'lightgbm', 'xgboost', 'catboost',
        'ultralytics', 'IPython', 'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
"""

_SPEC_ONEFILE = r"""
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=__APP_NAME__,
    debug=__CONSOLE__,
    bootloader_ignore_signals=False,
    strip=False,
    upx=__UPX__,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=__CONSOLE__,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    __ICON_LINE__
)
"""

_SPEC_ONEDIR = r"""
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=__APP_NAME__,
    debug=__CONSOLE__,
    strip=False,
    upx=__UPX__,
    upx_exclude=[],
    console=__CONSOLE__,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    __ICON_LINE__
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=__UPX__,
    upx_exclude=[],
    name=__APP_NAME__,
)
"""


def _write_spec(onedir: bool, debug: bool, upx: bool) -> Path:
    icon = find_icon()
    icon_line = f"icon={repr(str(icon))}," if icon else "# icon=None"

    datas = collect_bundled_datas()
    print(f"[번들] 내장 소스 {len(datas)}개 파일 (carbon_calculator + main.py + build_exe.py 등)")

    analysis = (
        _SPEC_ANALYSIS
        .replace("__ENTRY__", repr(str(ENTRY)))
        .replace("__HERE__",  repr(str(HERE)))
        .replace("__DATAS__", repr(datas))
    )

    exe_tmpl = _SPEC_ONEDIR if onedir else _SPEC_ONEFILE
    exe_section = (
        exe_tmpl
        .replace("__APP_NAME__",  repr(APP_NAME))
        .replace("__CONSOLE__",   "True" if debug else "False")
        .replace("__UPX__",       "True" if upx else "False")
        .replace("__ICON_LINE__", icon_line)
    )

    spec_dir = HERE / "build"
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_path = spec_dir / f"{APP_NAME}.spec"
    spec_path.write_text(analysis + exe_section, encoding="utf-8")
    return spec_path


# ─────────────────────────── 진입점 ───────────────────────────

def main() -> int:
    args = parse_args()

    if not ENTRY.exists():
        sys.exit(f"[오류] 진입점 파일을 찾을 수 없습니다: {ENTRY}")

    if args.clean_cache:
        clean_build_artifacts()

    build_venv = ensure_build_venv(rebuild=args.rebuild_venv)

    spec_path = _write_spec(onedir=args.onedir, debug=args.debug, upx=args.upx)

    python_exe = _venv_python(build_venv)
    if not python_exe.exists():
        sys.exit(f"[오류] 빌드 venv Python 을 찾을 수 없습니다: {python_exe}")

    print()
    print("=" * 70)
    print("PyInstaller 빌드 시작 (updater)")
    print(f"  진입점:    {ENTRY}")
    print(f"  spec:      {spec_path}")
    print(f"  앱 이름:   {APP_NAME}")
    print(f"  빌드 환경: {build_venv}")
    print(f"  모드:      {'onedir' if args.onedir else 'onefile'}")
    print(f"  콘솔:      {'표시' if args.debug else '숨김 (GUI)'}")
    print("=" * 70)

    result = subprocess.run(
        [
            str(python_exe), "-m", "PyInstaller",
            str(spec_path),
            "--noconfirm",
            "--clean",
            f"--workpath={HERE / 'build'}",
            f"--distpath={HERE / 'dist'}",
        ],
        cwd=str(HERE),
    )

    if result.returncode != 0:
        print()
        print("=" * 70)
        print("[실패] PyInstaller 빌드가 실패했습니다.")
        print("=" * 70)
        return 1

    dist_dir = HERE / "dist"
    if args.onedir:
        out     = dist_dir / APP_NAME / f"{APP_NAME}{_EXE_EXT}"
        out_dir = dist_dir / APP_NAME
    else:
        out     = dist_dir / f"{APP_NAME}{_EXE_EXT}"
        out_dir = None

    print()
    print("=" * 70)
    if out.exists():
        exe_mb = out.stat().st_size / 1048576
        print(f"[성공] 빌드 완료: {out}")
        print(f"       exe 크기: {exe_mb:.1f} MB")
        if out_dir:
            dir_mb = sum(f.stat().st_size for f in out_dir.rglob("*") if f.is_file()) / 1048576
            print(f"       폴더 합계: {dir_mb:.1f} MB")
        print()
        print("  ── 배포 방법 ──────────────────────────────────────────────")
        print(f"  {out.name} 를 Code 폴더(build_exe.py 와 같은 위치)에 복사하세요.")
        print("  사용자는 이 exe 만 더블클릭하면 JSON 로드 → 빌드를 실행할 수 있습니다.")
        print("  ────────────────────────────────────────────────────────────")
    else:
        print(f"[실패] 산출물을 찾을 수 없습니다: {out}")
    print("=" * 70)

    return 0 if out.exists() else 1


if __name__ == "__main__":
    sys.exit(main())

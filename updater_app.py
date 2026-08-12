# -*- coding: utf-8 -*-
"""
수종 데이터 업데이터 (자체 완결형).

이 프로그램은 **탄소저장량측정모듈(main.py) 의 전체 코드 로직을 내부에 내장**하고
있어, 소스 폴더 없이 이 exe 하나만으로 새 수종 데이터(JSON)를 반영한 실행파일을
만들 수 있다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
동작 방식
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[① exe 재빌드 — 자체 완결]  통합 species_data.json 을 입력받아,
   내장된 소스(carbon_calculator + main.py + build_exe.py)를 임시 작업폴더로
   풀고 그 안에 JSON 을 넣은 뒤 PyInstaller 로 새 탄소저장량측정모듈.exe 를 빌드한다.
   → 소스 트리를 옆에 둘 필요 없음. (단, PC 에 Python 3.10+ 이 있어야 컴파일 가능)

[② JSON 적용 — Python 불필요]  기존 탄소저장량측정모듈.exe 옆에 JSON 을 복사만 한다.
   다음 실행 시 자동 반영. 재빌드가 필요 없을 때 가장 빠른 경로.

JSON 양식:  species_data.json (통합본 — 교목·관목·국내·국외 4개 섹션)

실행:
    python updater_app.py        (개발 모드)
    수종데이터업데이터.exe        (배포 모드 — 단독 실행)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPlainTextEdit, QPushButton,
    QVBoxLayout, QWidget, QCheckBox,
)

_IS_EXE = hasattr(sys, '_MEIPASS')
HERE = Path(sys.executable).parent if _IS_EXE else Path(__file__).resolve().parent

# 내장 소스 루트:
#   frozen  → PyInstaller 가 _MEIPASS/bundled_src 로 풀어놓은 소스
#   dev     → 이 파일이 있는 Code 폴더 자체
if _IS_EXE:
    SRC_ROOT = Path(sys._MEIPASS) / "bundled_src"   # type: ignore[attr-defined]
else:
    SRC_ROOT = HERE

BUILD_VENV    = Path.home() / ".carboncalc_build_venv"
JSON_NAME     = "species_data.json"

# ── 플랫폼별 venv 레이아웃 / 실행파일 확장자 ──────────────────────────────
_VENV_BIN     = "Scripts" if os.name == "nt" else "bin"
_EXE_EXT      = ".exe" if os.name == "nt" else ""
MAIN_APP_NAME = "탄소저장량측정모듈"
MAIN_EXE_NAME = f"{MAIN_APP_NAME}{_EXE_EXT}"

# 작업폴더로 복사할 때 제외할 항목
_COPY_IGNORE = shutil.ignore_patterns(
    "build", "dist", "__pycache__", "*.pyc", ".git",
    ".build_venv", "*.spec",
)


def _find_python() -> Path | None:
    """빌드용 Python 탐색: 빌드 venv → 시스템 PATH."""
    p = BUILD_VENV / _VENV_BIN / f"python{_EXE_EXT}"
    if p.exists():
        return p
    for name in ("python", "python3"):
        found = shutil.which(name)
        if found:
            try:
                r = subprocess.run([found, "--version"], capture_output=True, timeout=5)
                if r.returncode == 0:
                    return Path(found)
            except Exception:
                pass
    return None


def _auto_find_main_exe() -> Path | None:
    """탄소저장량측정모듈.exe 를 자동 탐색 (현재 폴더 / dist/)."""
    for candidate in [
        HERE / MAIN_EXE_NAME,
        HERE / "dist" / MAIN_EXE_NAME,
        HERE / "dist" / MAIN_EXE_NAME.replace(".exe", "") / MAIN_EXE_NAME,
    ]:
        if candidate.exists():
            return candidate
    return None


# ─────────────────────────── JSON 검증 ───────────────────────────

def _validate_species_json(path: Path) -> tuple[bool, str]:
    """통합 species_data.json 검증. 4개 섹션 중 하나 이상 존재하면 유효."""
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        return False, f"JSON 파싱 오류: {e}"

    n_tree = len(data.get('TREE_BASE', {}))
    n_shrub = len(data.get('SHRUB_SPECIES', {}))
    n_dom = len(data.get('DOMESTIC_SPECIES', {}))
    n_for = len(data.get('FOREIGN_SPECIES', {}))

    if (n_tree + n_shrub + n_dom + n_for) == 0:
        return False, ("유효한 수종 섹션이 없습니다. "
                       "TREE_BASE / SHRUB_SPECIES / DOMESTIC_SPECIES / FOREIGN_SPECIES 중 "
                       "하나 이상이 필요합니다.")

    return True, f"교목 {n_tree} · 관목 {n_shrub} · 국내 {n_dom} · 국외 {n_for}종"


# ─────────────────────────── 빌드 워커 ───────────────────────────

class BuildWorker(QThread):
    """임시 작업폴더 구성 → build_exe.py 실행 → 산출물 복사 를 백그라운드로 수행."""
    log_line = pyqtSignal(str)
    finished = pyqtSignal(bool, str)   # (성공여부, 산출물 경로 또는 오류메시지)

    def __init__(self, json_path: Path, out_dir: Path, options: list[str]):
        super().__init__()
        self.json_path = json_path
        self.out_dir = out_dir
        self.options = options

    def _emit(self, msg: str):
        self.log_line.emit(msg)

    def run(self):
        workdir = None
        try:
            python = _find_python()
            if python is None:
                self.finished.emit(False,
                    "Python 인터프리터를 찾을 수 없습니다. Python 3.10+ 를 설치하세요.")
                return

            if not (SRC_ROOT / "build_exe.py").exists():
                self.finished.emit(False,
                    f"내장 소스를 찾을 수 없습니다: {SRC_ROOT}\n"
                    "updater 를 build_updater.py 로 다시 빌드하세요.")
                return

            # ── 1) 내장 소스를 임시 작업폴더로 복사 ──────────────────────
            workdir = Path(tempfile.mkdtemp(prefix="carboncalc_build_"))
            self._emit(f"[1/4] 작업폴더 준비: {workdir}")
            shutil.copytree(SRC_ROOT, workdir, dirs_exist_ok=True, ignore=_COPY_IGNORE)

            # ── 2) 사용자 JSON 투입 (구 carbon1/2 파일은 충돌 방지 위해 제거) ──
            for _old in ("carbon1_species_data.json", "carbon2_species_data.json"):
                _p = workdir / _old
                if _p.exists():
                    _p.unlink()
            shutil.copy2(self.json_path, workdir / JSON_NAME)
            self._emit(f"[2/4] 수종 데이터 적용: {self.json_path.name} → {JSON_NAME}")

            # ── 3) build_exe.py 실행 (PyInstaller) ──────────────────────
            cmd = [str(python), str(workdir / "build_exe.py")] + self.options
            self._emit(f"[3/4] 빌드 시작: {' '.join(cmd)}")
            self._emit("      (최초 실행 시 빌드 전용 venv 생성으로 수 분 소요)")
            self._emit("=" * 70)

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace',
                cwd=str(workdir),
            )
            for line in proc.stdout:
                self._emit(line.rstrip())
            proc.wait()

            if proc.returncode != 0:
                self.finished.emit(False, "PyInstaller 빌드가 실패했습니다. 위 로그를 확인하세요.")
                return

            # ── 4) 산출물 복사 ─────────────────────────────────────────
            onedir = "--onedir" in self.options
            if onedir:
                produced = workdir / "dist" / "탄소저장량측정모듈"
            else:
                produced = workdir / "dist" / MAIN_EXE_NAME

            if not produced.exists():
                self.finished.emit(False, f"산출물을 찾을 수 없습니다: {produced}")
                return

            self.out_dir.mkdir(parents=True, exist_ok=True)
            self._emit("=" * 70)
            self._emit(f"[4/4] 산출물 복사 → {self.out_dir}")

            if onedir:
                dest = self.out_dir / "탄소저장량측정모듈"
                if dest.exists():
                    shutil.rmtree(dest, ignore_errors=True)
                shutil.copytree(produced, dest)
                final = dest / MAIN_EXE_NAME
            else:
                final = self.out_dir / MAIN_EXE_NAME
                shutil.copy2(produced, final)

            self.finished.emit(True, str(final))

        except Exception as e:
            self.finished.emit(False, f"[오류] {e}")
        finally:
            if workdir and workdir.exists():
                shutil.rmtree(workdir, ignore_errors=True)


# ─────────────────────────── UI 헬퍼 ───────────────────────────

class FilePickRow(QWidget):
    def __init__(self, label: str, btn_label: str = "열기...", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label_w = QLabel(label)
        self.label_w.setFixedWidth(215)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("파일/폴더 경로를 선택하거나 직접 입력하세요")
        self.btn = QPushButton(btn_label)
        self.btn.setFixedWidth(75)
        layout.addWidget(self.label_w)
        layout.addWidget(self.edit)
        layout.addWidget(self.btn)

    @property
    def path(self) -> Path | None:
        t = self.edit.text().strip()
        return Path(t) if t else None


# ─────────────────────────── 메인 창 ───────────────────────────

class UpdaterWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("수종 데이터 업데이터 (자체 완결형) — 탄소저장량 측정 모듈")
        self.setMinimumWidth(960)
        self._worker: BuildWorker | None = None
        self._out_user_edited = False   # 출력 폴더를 사용자가 직접 지정했는지
        self._setup_ui()
        self._auto_detect()

    def _setup_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setSpacing(10)
        v.setContentsMargins(12, 12, 12, 12)

        # ── 통합 JSON 선택 ─────────────────────────────────────────
        json_grp = QGroupBox("수종 데이터 JSON (통합 species_data.json)")
        jl = QVBoxLayout(json_grp)
        self.json_row = FilePickRow("species_data.json")
        self.json_row.btn.clicked.connect(self._pick_json)
        self.json_row.edit.textChanged.connect(self._recheck_json)
        self.json_status = QLabel("— 파일을 선택하면 검증됩니다")
        self.json_status.setStyleSheet("color: gray; margin-left: 223px;")
        jl.addWidget(self.json_row)
        jl.addWidget(self.json_status)
        v.addWidget(json_grp)

        # ── ① exe 재빌드 (자체 완결) ───────────────────────────────
        build_grp = QGroupBox("① exe 재빌드   —   내장 소스로 새 탄소저장량측정모듈.exe 생성 (권장)")
        build_grp.setStyleSheet("QGroupBox { font-weight: bold; }")
        bl = QVBoxLayout(build_grp)

        _note = QLabel(
            "이 업데이터에 내장된 전체 코드 로직을 사용해 JSON 이 반영된 새 exe 를 만듭니다. "
            "소스 폴더가 옆에 없어도 됩니다.\n"
            "※ 컴파일에는 이 PC 에 Python 3.10 이상이 필요합니다 (최초 1회 빌드 환경 자동 구성).")
        _note.setStyleSheet("color: #555; font-size: 11px;")
        _note.setWordWrap(True)
        bl.addWidget(_note)

        self.out_row = FilePickRow("출력 폴더 (exe 저장 위치)", "폴더...")
        self.out_row.btn.clicked.connect(self._pick_out_dir)
        self.out_row.edit.textEdited.connect(self._mark_out_edited)
        bl.addWidget(self.out_row)

        opt_row = QHBoxLayout()
        self.onedir_cb = QCheckBox("onedir 모드")
        self.debug_cb  = QCheckBox("디버그 콘솔")
        self.upx_cb    = QCheckBox("UPX 압축")
        self.clean_cb  = QCheckBox("캐시 초기화")
        for cb in (self.onedir_cb, self.debug_cb, self.upx_cb, self.clean_cb):
            opt_row.addWidget(cb)
        opt_row.addStretch()
        bl.addLayout(opt_row)

        self.build_btn = QPushButton("새 exe 빌드 (PyInstaller)")
        self.build_btn.setFixedHeight(42)
        f = self.build_btn.font(); f.setBold(True); f.setPointSize(11)
        self.build_btn.setFont(f)
        self.build_btn.clicked.connect(self._start_build)
        bl.addWidget(self.build_btn)

        self.build_status = QLabel("준비")
        self.build_status.setAlignment(Qt.AlignCenter)
        bl.addWidget(self.build_status)
        v.addWidget(build_grp)

        # ── ② JSON 적용 (Python 불필요) ────────────────────────────
        apply_grp = QGroupBox("② JSON 적용   —   기존 exe 옆에 복사만 (Python 불필요)")
        al = QVBoxLayout(apply_grp)
        _anote = QLabel(
            "이미 만들어진 탄소저장량측정모듈.exe 가 있다면, 그 옆에 JSON 을 복사해 "
            "다음 실행 시 즉시 반영합니다. 재빌드가 필요 없을 때 사용하세요.")
        _anote.setStyleSheet("color: #555; font-size: 11px;")
        _anote.setWordWrap(True)
        al.addWidget(_anote)

        self.exe_row = FilePickRow("탄소저장량측정모듈.exe 위치", "찾기...")
        self.exe_row.btn.clicked.connect(self._pick_exe)
        self.exe_row.edit.textChanged.connect(self._recheck_exe)
        self.exe_status = QLabel("")
        self.exe_status.setStyleSheet("margin-left: 223px;")
        al.addWidget(self.exe_row)
        al.addWidget(self.exe_status)

        self.apply_btn = QPushButton("JSON 적용 (복사)")
        self.apply_btn.setFixedHeight(36)
        self.apply_btn.clicked.connect(self._apply_json)
        al.addWidget(self.apply_btn)

        self.apply_status = QLabel("준비")
        self.apply_status.setAlignment(Qt.AlignCenter)
        al.addWidget(self.apply_status)
        v.addWidget(apply_grp)

        # ── 로그 ──────────────────────────────────────────────────
        log_grp = QGroupBox("로그")
        ll = QVBoxLayout(log_grp)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 9))
        self.log.setMinimumHeight(220)
        ll.addWidget(self.log)
        v.addWidget(log_grp)

    # ── 자동 탐색 ──────────────────────────────────────────────────

    def _auto_detect(self):
        # 내장/근처 JSON 자동 채움
        for cand in (HERE / JSON_NAME, SRC_ROOT / JSON_NAME):
            if cand.exists():
                self.json_row.edit.setText(str(cand))
                break
        # 출력 폴더 기본값 = updater 위치
        self.out_row.edit.setText(str(HERE))
        # 기존 exe 자동 탐색
        exe = _auto_find_main_exe()
        if exe:
            self.exe_row.edit.setText(str(exe))

    # ── JSON 선택·검증 ──────────────────────────────────────────────

    def _pick_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "통합 species_data.json 선택", str(HERE), "JSON 파일 (*.json)")
        if path:
            self.json_row.edit.setText(path)
            # "해당 디렉토리에 빌드" — 출력 폴더를 선택한 JSON 이 있는 폴더로 자동 지정
            # (사용자가 이미 직접 바꾼 경우는 존중)
            if not self._out_user_edited:
                self.out_row.edit.blockSignals(True)
                self.out_row.edit.setText(str(Path(path).parent))
                self.out_row.edit.blockSignals(False)

    def _recheck_json(self):
        p = self.json_row.path
        if not p:
            self.json_status.setText("— 파일을 선택하면 검증됩니다")
            self.json_status.setStyleSheet("color: gray; margin-left: 223px;")
        elif p.exists():
            ok, msg = _validate_species_json(p)
            color = "green" if ok else "red"
            mark = "✓" if ok else "✗"
            self.json_status.setText(f"{mark} {msg}")
            self.json_status.setStyleSheet(f"color: {color}; margin-left: 223px;")
        else:
            self.json_status.setText("파일을 찾을 수 없습니다.")
            self.json_status.setStyleSheet("color: red; margin-left: 223px;")

    def _pick_out_dir(self):
        d = QFileDialog.getExistingDirectory(self, "출력 폴더 선택", str(HERE))
        if d:
            self._out_user_edited = True
            self.out_row.edit.setText(d)

    def _mark_out_edited(self, _text: str):
        self._out_user_edited = True

    # ── exe 선택 (② 모드) ──────────────────────────────────────────

    def _pick_exe(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "탄소저장량측정모듈.exe 선택", str(HERE), "실행 파일 (*.exe)")
        if path:
            self.exe_row.edit.setText(path)

    def _recheck_exe(self):
        p = self.exe_row.path
        if p and p.exists():
            self.exe_status.setText(f"✓ {p}")
            self.exe_status.setStyleSheet("color: green; margin-left: 223px;")
        elif p:
            self.exe_status.setText("파일을 찾을 수 없습니다.")
            self.exe_status.setStyleSheet("color: red; margin-left: 223px;")
        else:
            self.exe_status.setText("")

    # ── ① exe 재빌드 ────────────────────────────────────────────────

    def _start_build(self):
        if self._worker and self._worker.isRunning():
            return

        json_path = self.json_row.path
        if not json_path or not json_path.exists():
            self._set_build_status("먼저 species_data.json 을 선택하세요.", "red")
            return
        ok, msg = _validate_species_json(json_path)
        if not ok:
            self._set_build_status(f"JSON 오류: {msg}", "red")
            return

        out_dir = self.out_row.path
        if not out_dir:
            self._set_build_status("출력 폴더를 지정하세요.", "red")
            return

        options: list[str] = []
        if self.onedir_cb.isChecked(): options.append("--onedir")
        if self.debug_cb.isChecked():  options.append("--debug")
        if self.upx_cb.isChecked():    options.append("--upx")
        if self.clean_cb.isChecked():  options.append("--clean-cache")

        self.log.clear()
        self.build_btn.setEnabled(False)
        self._set_build_status("빌드 중...", "black")

        self._worker = BuildWorker(json_path, out_dir, options)
        self._worker.log_line.connect(self._append_log)
        self._worker.finished.connect(self._on_build_done)
        self._worker.start()

    def _on_build_done(self, success: bool, info: str):
        self.build_btn.setEnabled(True)
        self.log.appendPlainText("=" * 70)
        if success:
            self._set_build_status("빌드 완료!", "green")
            self.log.appendPlainText(f"[완료] 새 실행파일: {info}")
        else:
            self._set_build_status("빌드 실패 — 로그 확인", "red")
            self.log.appendPlainText(f"[실패] {info}")

    def _set_build_status(self, text: str, color: str):
        self.build_status.setText(text)
        self.build_status.setStyleSheet(f"color: {color};")

    # ── ② JSON 적용 ────────────────────────────────────────────────

    def _apply_json(self):
        json_path = self.json_row.path
        if not json_path or not json_path.exists():
            self.apply_status.setText("먼저 species_data.json 을 선택하세요.")
            self.apply_status.setStyleSheet("color: red;")
            return
        ok, _ = _validate_species_json(json_path)
        if not ok:
            self.apply_status.setText("JSON 검증에 실패했습니다 (상단 상태 확인).")
            self.apply_status.setStyleSheet("color: red;")
            return

        exe_path = self.exe_row.path
        if not exe_path or not exe_path.exists():
            self.apply_status.setText("탄소저장량측정모듈.exe 위치를 선택하세요.")
            self.apply_status.setStyleSheet("color: red;")
            return

        target_dir = exe_path.parent
        dst = target_dir / JSON_NAME
        shutil.copy2(json_path, dst)
        # 구버전 분리 JSON 이 남아 통합본을 가리지 않도록 정리
        removed = []
        for _old in ("carbon1_species_data.json", "carbon2_species_data.json"):
            _p = target_dir / _old
            if _p.exists():
                try:
                    _p.unlink()
                    removed.append(_old)
                except Exception:
                    pass

        self.log.clear()
        self.log.appendPlainText(f"[완료] {JSON_NAME} → {dst}")
        if removed:
            self.log.appendPlainText(f"[정리] 구버전 JSON 제거: {', '.join(removed)}")
        self.log.appendPlainText("")
        self.log.appendPlainText("탄소저장량측정모듈.exe 를 다시 실행하면 새 수종 데이터가 적용됩니다.")
        self.apply_status.setText("완료 — JSON 복사됨")
        self.apply_status.setStyleSheet("color: green;")

    # ── 로그 ──────────────────────────────────────────────────────

    def _append_log(self, line: str):
        self.log.appendPlainText(line)
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())


def main():
    app = QApplication(sys.argv)
    win = UpdaterWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

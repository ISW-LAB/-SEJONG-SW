# 세종수목원 복원본지 탄소저장량 측정 모듈

> English version: [README.en.md](README.en.md)

MATLAB App Designer 원본(`Carbon_251002_5.mlapp` / `Carbon2_251013_1.mlapp`)을 Python(PyQt5)으로
포팅한 프로젝트. **탄소저장량측정모듈**(핵심 소프트웨어)과, 수종 데이터를 갱신·재빌드하는
**수종데이터업데이터** 두 개의 실행파일을 만든다.

## 폴더 구조

```
Code/
├── main.py                 ← 실행 진입점 (Carbon1·Carbon2 통합 탭 창)
├── build_exe.py             ← 핵심 소프트웨어 빌드 스크립트 (main.py → 탄소저장량측정모듈.exe)
├── build_updater.py         ← 업데이터 빌드 스크립트 (updater_app.py → 수종데이터업데이터.exe)
├── updater_app.py           ← 업데이터 앱 소스 (build_exe.py 로직을 내장 실행)
├── updater_빌드.bat         ← build_updater.py 실행 배치 파일 (Windows)
├── installer.iss            ← Inno Setup 설치 마법사(Setup.exe) 스크립트
├── requirements.txt         ← 실행 의존성 (PyQt5, matplotlib, numpy, openpyxl, Pillow)
├── species_data.json        ← 통합 수종 데이터 (교목·관목·국내·국외)
├── icon.ico                 ← 앱 아이콘
└── carbon_calculator/       ← 기능별 핵심 패키지
    ├── data.py / data2.py          — 수종 계수·상대생장식 데이터
    ├── calculations.py             — 탄소저장량 계산 로직
    ├── equation_eval.py            — 문자열 수식 평가
    ├── widgets.py / plotting.py    — 공용 UI 위젯 / 그래프
    ├── theme.py / font_config.py / ui_scale.py  — 테마·폰트·DPI 스케일
    ├── excel_export.py             — 결과 Excel 내보내기
    ├── main_window.py              — Carbon1(자생복원종) 화면
    ├── main_window2.py             — Carbon2(국내·국외 통합) 화면
    └── combined_window.py          — 통합 메인 윈도우(지역별 동적 탭)
```

---

## 0. 사전 준비 (최초 1회)

```powershell
pip install -r requirements.txt
```

빌드(`build_exe.py`, `build_updater.py`)는 `pyinstaller` 를 별도 설치할 필요 없이,
전용 빌드 venv(`~\.carboncalc_build_venv`)를 자동으로 만들어 그 안에 알아서 설치한다.
(최초 빌드 시 몇 분 소요, 이후에는 venv 를 재사용해 즉시 시작)

---

## 1. 개발 모드로 실행

```powershell
python main.py
```

Carbon1(자생복원종)·Carbon2(국내·국외 통합)를 하나의 창에서 지역별 탭으로 관리하는 통합 UI가 뜬다.

---

## 2. 핵심 소프트웨어(탄소저장량측정모듈) 빌드

```powershell
python build_exe.py              # onefile (단일 exe, 배포 용이) — 기본
python build_exe.py --onedir     # 폴더 형태 (시작 속도 빠름)
python build_exe.py --debug      # 콘솔창 표시 (오류 진단용)
python build_exe.py --upx        # UPX 압축 활성화 (크기 추가 절감)
python build_exe.py --clean-cache        # 빌드 전 build/, dist/ 삭제 후 새로 빌드
python build_exe.py --rebuild-venv       # 빌드 전용 venv 강제 재생성
```

- 산출물: `dist\탄소저장량측정모듈.exe` (onefile) 또는 `dist\탄소저장량측정모듈\` (onedir)
- `species_data.json` 이 프로젝트 루트에 있으면 빌드 시 함께 동봉되어 실행 시 자동 반영된다.
- exe 가 실행 직후 꺼지는 등 문제가 있으면 `--debug` 로 다시 빌드해 콘솔 로그를 확인한다.

---

## 3. 수종데이터업데이터 빌드

```powershell
python build_updater.py
```

또는 Windows 배치로:

```powershell
updater_빌드.bat
```

- 산출물: `dist\수종데이터업데이터.exe`
- 이 exe 는 `carbon_calculator` + `main.py` + `build_exe.py` 등 **핵심 소프트웨어의 전체 소스를
  내부에 번들**하고 있어, 소스 폴더 없이 이 exe 하나만 배포해도 동작한다.
- 배포된 `수종데이터업데이터.exe` 는 실행 즉시 `species_data.json` 을 **표로 열어 편집**할 수 있다
  (교목·관목·국내·국외 4개 탭, 셀 더블클릭 수정, 수종 추가/삭제, 교목의 환경별 계수 편집,
  저장 전 검증, 저장 시 `.bak` 백업). 편집 후에는 두 가지 방식으로 반영한다:
  1. **exe 재빌드** — 새 `species_data.json` 을 입력받아 내장 소스로 새
     `탄소저장량측정모듈.exe` 를 다시 빌드 (PC 에 Python 3.10+ 필요)
  2. **JSON 적용** — 기존 `탄소저장량측정모듈.exe` 옆에 `species_data.json` 만 복사
     (Python 불필요, 다음 실행부터 즉시 반영)

---

## 4. 설치 마법사(Setup.exe) 만들기 — 선택 사항

일반 사용자 배포용으로 설치·시작메뉴·제거 기능이 있는 설치 프로그램을 만들고 싶다면:

1. `python build_exe.py --onedir` 로 폴더형 빌드 (`dist\탄소저장량측정모듈\` 생성)
2. [Inno Setup 6](https://jrsoftware.org/isdl.php) 설치
3. 다음 중 하나로 컴파일:
   - Inno Setup Compiler 에서 `installer.iss` 열고 `Build > Compile`
   - 명령줄: `"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss`
4. 산출물: `installer_output\탄소저장량측정모듈_Setup_3.0.exe`

---

## 5. 수종 데이터 갱신

`수종데이터업데이터.exe` 의 표 편집기에서 수종·계수·식·범위를 고쳐 저장하거나(권장),
`species_data.json` 을 직접 수정한 뒤 `python build_exe.py` 로 재빌드한다.
이미 배포된 exe 에는 위 3번의 방식으로 반영한다. 새 수종을 추가할 때는 학명 열도 채워야
영문 모드에서 학명으로 표기된다.

---

## 문제 해결

| 증상 | 해결 |
|------|------|
| `ModuleNotFoundError: No module named 'PyQt5'` | `pip install -r requirements.txt` |
| exe 빌드 시 PyInstaller 관련 오류 | `python build_exe.py --rebuild-venv` 로 빌드 venv 재생성 |
| 한글 폰트가 깨져 보임 | Windows 기본 폰트 "맑은 고딕(Malgun Gothic)" 설치 여부 확인 |
| exe 실행 시 즉시 종료됨 | `python build_exe.py --debug` 로 재빌드 후 콘솔 오류 메시지 확인 |
| 글자가 너무 크거나 작음 | `carbon_calculator\font_config.py` 의 `FONT_SIZE_DELTA` 값 조정 |

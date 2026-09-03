@echo off
REM ============================================================
REM  탄소저장량측정모듈 실행 (conda)
REM  - tree-sim 브랜치는 pyvista>=0.48 → Python 3.10+ 환경(rudckd310)이 필요.
REM  - main 브랜치는 rudckd(3.9)로도 실행된다.
REM  기본 rudckd310, 없으면 rudckd 로 자동 대체.
REM ============================================================
chcp 65001 >nul
setlocal

set "CONDA_ROOT=%USERPROFILE%\anaconda3"
set "ENV_NAME=rudckd310"

if not exist "%CONDA_ROOT%\Scripts\activate.bat" (
    echo [오류] conda 를 찾을 수 없습니다: %CONDA_ROOT%
    echo        이 파일의 CONDA_ROOT 값을 실제 설치 경로로 수정하세요.
    pause
    exit /b 1
)

if not exist "%CONDA_ROOT%\envs\%ENV_NAME%\python.exe" (
    echo [안내] %ENV_NAME% 환경이 없어 rudckd 로 대체합니다.
    set "ENV_NAME=rudckd"
)

cd /d "%~dp0"

call "%CONDA_ROOT%\Scripts\activate.bat" "%ENV_NAME%"
if errorlevel 1 (
    echo [오류] conda 환경 "%ENV_NAME%" 활성화 실패
    pause
    exit /b 1
)

REM --- 사전 준비: 의존성 확인 (없을 때만 설치) ---
python -c "import PyQt5, matplotlib, numpy, openpyxl, PIL" 2>nul
if errorlevel 1 (
    echo [설치] 의존성이 없어 requirements.txt 를 설치합니다...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [오류] 의존성 설치 실패
        pause
        exit /b 1
    )
)

REM --- tree-sim 브랜치의 3D 시각화 의존성 확인 ---
findstr /c:"pyvista" requirements.txt >nul 2>&1
if not errorlevel 1 (
    python -c "import pyvista, pyvistaqt, vtk" 2>nul
    if errorlevel 1 (
        echo [설치] 3D 시각화 의존성이 없어 requirements.txt 를 설치합니다...
        python -m pip install -r requirements.txt
        if errorlevel 1 (
            echo [오류] 3D 의존성 설치 실패 ^(Python 3.10 이상 환경이 필요합니다^)
            pause
            exit /b 1
        )
    )
)

echo [실행] %ENV_NAME% / python main.py
python main.py
if errorlevel 1 pause

endlocal

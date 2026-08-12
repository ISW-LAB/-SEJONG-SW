@echo off
REM ============================================================
REM  수종데이터업데이터.exe 빌드 (자체 완결형)
REM  - 탄소저장량측정모듈 전체 소스를 내장한 updater.exe 를 만든다.
REM  - Windows + Python 3.10 이상 필요.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo [1/1] 수종데이터업데이터.exe 빌드 시작...
echo.

python build_updater.py %*
if errorlevel 1 (
    echo.
    echo [실패] 빌드에 실패했습니다. 위 로그를 확인하세요.
    echo        Python 3.10 이상이 설치되어 있는지 확인하세요.
    pause
    exit /b 1
)

echo.
echo [완료] dist\수종데이터업데이터.exe 생성됨.
echo        이 exe 하나만 배포하면, 사용자는 UI 에서 species_data.json 을
echo        선택해 원하는 폴더에 탄소저장량측정모듈.exe 를 빌드할 수 있습니다.
echo.
pause

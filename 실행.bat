@echo off
chcp 65001 > nul
cd /d "%~dp0"
python app.py
if errorlevel 1 (
  echo.
  echo Flask 실행에 실패했습니다. README.md의 설치 안내를 확인하세요.
  pause
)

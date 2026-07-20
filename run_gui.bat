@echo off
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
    echo [Loi] Chua cai "uv" tren may nay.
    echo Cai tai: https://docs.astral.sh/uv/getting-started/installation/
    echo Sau khi cai xong, chay lai file nay.
    pause
    exit /b 1
)

echo Dang kiem tra / cai dependency (chi mat thoi gian lan dau)...
uv sync
if errorlevel 1 (
    echo [Loi] "uv sync" that bai, xem log o tren.
    pause
    exit /b 1
)

echo.
echo Dang mo Genshin AI Account Manager...
uv run gui_app.py

if errorlevel 1 (
    echo.
    echo [Loi] App bi thoat voi loi, xem log o tren.
    pause
)

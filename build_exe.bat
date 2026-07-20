@echo off
setlocal
cd /d "%~dp0"

echo Dang cai pyinstaller vao venv cua project...
uv pip install pyinstaller
if errorlevel 1 (
    echo [Loi] Cai pyinstaller that bai.
    pause
    exit /b 1
)

echo.
echo Dang build GenshinAIAccountManager.exe (co the mat 1-2 phut)...
uv run pyinstaller --noconfirm --onefile --windowed ^
    --name "GenshinAIAccountManager" ^
    --add-data "templates;templates" ^
    --add-data "gui\style.qss;gui" ^
    gui_app.py

if errorlevel 1 (
    echo [Loi] Build that bai, xem log o tren.
    pause
    exit /b 1
)

echo Dang copy config.yaml mac dinh ra canh file .exe (config.yaml doc/ghi
echo canh .exe, khac voi templates/style.qss la resource dong goi ben trong)...
copy /Y config.yaml dist\config.yaml >nul

echo.
echo Xong! File .exe nam trong thu muc dist\GenshinAIAccountManager.exe
echo (kem theo dist\config.yaml - GIU NGUYEN canh .exe, khong xoa/di chuyen rieng)
echo Lan dau chay .exe, no se tu tao .env / genshin_agent.db canh .exe.
echo Nen de ca thu muc dist\ o 1 cho rieng, khong gop chung Desktop voi file khac.
pause

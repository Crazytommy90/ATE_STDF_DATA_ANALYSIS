@echo off
echo ========================================
echo STDF Analysis System - Single File Build
echo ========================================
echo.
echo Description:
echo - Generate single exe file
echo - Easy to distribute
echo - First startup will be slower (need to extract)
echo.

echo [1/4] Clean old files...
if exist "dist" (
    echo Deleting dist directory...
    rmdir /s /q dist
)
if exist "build" (
    echo Deleting build directory...
    rmdir /s /q build
)

echo.
echo [2/4] Check required files...
if not exist "build_exe_onefile.spec" (
    echo ERROR: build_exe_onefile.spec not found!
    pause
    exit /b 1
)
echo [OK] build_exe_onefile.spec exists

if not exist "app.py" (
    echo ERROR: app.py not found!
    pause
    exit /b 1
)
echo [OK] app.py exists

if not exist "icon_swf.ico" (
    echo WARNING: icon_swf.ico not found, will use default icon
) else (
    echo [OK] icon_swf.ico exists
)

echo.
echo [3/4] Check Python modules...
python -c "import PySide2" 2>nul
if errorlevel 1 (
    echo ERROR: PySide2 not installed!
    echo Please run: pip install PySide2
    pause
    exit /b 1
)
echo [OK] PySide2 installed

python -c "import tables" 2>nul
if errorlevel 1 (
    echo ERROR: tables not installed!
    echo Please run: pip install tables
    pause
    exit /b 1
)
echo [OK] tables installed

python -c "import pandas" 2>nul
if errorlevel 1 (
    echo ERROR: pandas not installed!
    echo Please run: pip install pandas
    pause
    exit /b 1
)
echo [OK] pandas installed

echo.
echo [4/4] Start single file packaging...
echo NOTE: This may take a while, please wait...
python -m PyInstaller build_exe_onefile.spec --clean --log-level=INFO

if errorlevel 1 (
    echo.
    echo ========================================
    echo Build FAILED!
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo Single File Build SUCCESS!
echo ========================================
echo.
echo Output file: dist\STDF_Analysis_V1.exe
echo File size: Approx 200-300MB
echo.
echo Advantages:
echo - Single exe file, easy to distribute
echo - No additional files needed
echo.
echo Disadvantages:
echo - Slower first startup (needs to extract to temp directory)
echo - Larger file size
echo.
echo New features:
echo - Added "Open TEMP folder" function (left toolbar)
echo - All logs recorded to logger.log file
echo - Fixed KeyError and AttributeError during data loading
echo.
echo Usage:
echo 1. Run dist\STDF_Analysis_V1.exe directly
echo 2. First run will auto-create C:\1_STDF cache directory
echo 3. Click "Open TEMP folder" button in left toolbar to test
echo 4. All operation logs saved in logger.log
echo.
pause
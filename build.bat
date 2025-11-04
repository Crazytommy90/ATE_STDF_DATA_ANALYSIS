@echo off
echo ========================================
echo STDF Analysis System - Multi-file Build
echo ========================================
echo.

echo [1/4] Cleaning old files...
if exist "dist" (
    echo Deleting dist directory...
    rmdir /s /q dist
)
if exist "build" (
    echo Deleting build directory...
    rmdir /s /q build
)

echo.
echo [2/4] Checking required files...
if not exist "hook-tables.py" (
    echo ERROR: hook-tables.py not found!
    pause
    exit /b 1
)
echo [OK] hook-tables.py exists

if not exist "build_exe.spec" (
    echo ERROR: build_exe.spec not found!
    pause
    exit /b 1
)
echo [OK] build_exe.spec exists

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
echo [3/4] Checking Python modules...
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
echo [4/4] Starting build...
echo Using --clean parameter to ensure complete rebuild
python -m PyInstaller build_exe.spec --clean --log-level=INFO

if errorlevel 1 (
    echo.
    echo ========================================
    echo Build FAILED!
    echo ========================================
    echo.
    echo Please check:
    echo 1. Is tables library correctly installed
    echo 2. Does hook-tables.py exist
    echo 3. Is build_exe.spec configured correctly
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build SUCCESS!
echo ========================================
echo.
echo Output directory: dist\STDF_Analysis\
echo Main program: dist\STDF_Analysis\STDF_Analysis.exe
echo.
echo New features:
echo - Added "Open TEMP folder" function (left toolbar)
echo - All logs recorded to logger.log file
echo - Fixed KeyError and AttributeError during data loading
echo.
echo Test steps:
echo 1. cd dist\STDF_Analysis
echo 2. STDF_Analysis.exe
echo 3. Click "Open TEMP folder" button in left toolbar to test
echo 4. Load STDF file to test data analysis function
echo.
echo Notes:
echo - First run will auto-create C:\1_STDF cache directory
echo - Log file logger.log will record all operations
echo.
pause
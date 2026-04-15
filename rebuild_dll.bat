@echo off
echo 正在重新编译64位DLL...
cd parser_core\cpp_stdf2hdf5

"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" stdf_ctype.sln /p:Configuration=Release /p:Platform=x64 /t:Rebuild

if %ERRORLEVEL% EQU 0 (
    echo.
    echo 编译成功!
    echo 正在复制DLL...
    copy /Y "x64\Release\stdf_ctype.dll" "..\dll_parser\stdf_ctype.dll"
    echo.
    echo 完成!
) else (
    echo.
    echo 编译失败,错误码: %ERRORLEVEL%
)

cd ..\..
pause
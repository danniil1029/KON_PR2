@echo off
setlocal EnableExtensions
pushd "%~dp0" || exit /b 1
set "launcher=python"
where /q py.exe && set "launcher=py -3"
%launcher% -m src.main %*
set "result=%errorlevel%"
popd
exit /b %result%

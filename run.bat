@echo off
setlocal EnableExtensions
set "demo="
if "%~1"=="" set "demo=1"

pushd "%~dp0" || (
    if defined demo pause
    exit /b 1
)

if not exist "src\main.py" (
    echo Extract the entire ZIP before running this file.
    set "result=1"
    goto finish
)

set "launcher=python"
where /q py.exe && set "launcher=py -3"

if defined demo (
    %launcher% -m src.main --test --repo tests/fixtures/graph.json --package A --tree --output A.svg
) else (
    %launcher% -m src.main %*
)
set "result=%errorlevel%"

:finish
if defined demo (
    if "%result%"=="0" echo Open A.svg in your browser to see the graph.
    pause
)
popd
exit /b %result%

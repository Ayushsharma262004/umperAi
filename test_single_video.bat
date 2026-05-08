@echo off
REM Quick test script for single video

echo ========================================
echo UmpirAI Single Video Test
echo ========================================
echo.

if "%1"=="" (
    echo Usage: test_single_video.bat ^<video_path^>
    echo.
    echo Examples:
    echo   test_single_video.bat videos\w7.mp4
    echo   test_single_video.bat videos\lbw20_mirr.mp4
    echo.
    echo Available videos:
    dir /b videos\*.mp4
    echo.
    pause
    exit /b 1
)

echo Testing video: %1
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python run_full_pipeline.py %1

echo.
echo Test complete!
pause

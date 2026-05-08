@echo off
REM Batch test all videos

echo ========================================
echo UmpirAI Batch Video Testing
echo ========================================
echo.
echo This will process all videos in the videos directory
echo and generate a comprehensive report.
echo.
echo Press Ctrl+C to cancel, or
pause

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python test_all_videos.py

echo.
echo ========================================
echo Testing Complete!
echo ========================================
echo.
echo Reports generated:
echo   - test_report.json (detailed JSON)
echo   - test_summary.txt (readable summary)
echo.
pause

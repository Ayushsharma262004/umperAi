@echo off
echo ========================================
echo UmpirAI - Test All Cricket Videos
echo ========================================
echo.
echo This will process all videos in videos/ folder
echo and save output videos with detections.
echo.
pause

python test_all_cricket_videos.py

echo.
echo ========================================
echo Processing Complete!
echo ========================================
echo.
echo Output videos are in: output_videos/
echo.
pause

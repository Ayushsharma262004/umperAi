@echo off
REM Install YOLOv8 and Dependencies for UmpirAI

echo.
echo ======================================================================
echo 🏏 UmpirAI - Installing YOLOv8 and Dependencies
echo ======================================================================
echo.

echo 📦 Installing required packages...
echo    This may take 5-10 minutes depending on your internet speed
echo.

REM Install PyTorch (CPU version for compatibility)
echo [1/3] Installing PyTorch...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

REM Install OpenCV
echo.
echo [2/3] Installing OpenCV...
pip install opencv-python opencv-contrib-python

REM Install Ultralytics (YOLOv8)
echo.
echo [3/3] Installing YOLOv8 (Ultralytics)...
pip install ultralytics

echo.
echo ======================================================================
echo ✅ Installation Complete!
echo ======================================================================
echo.

echo 📥 Downloading YOLOv8 model...
python -c "from ultralytics import YOLO; model = YOLO('yolov8n.pt'); print('✅ YOLOv8n model downloaded!')"

echo.
echo ======================================================================
echo 🎉 Setup Complete!
echo ======================================================================
echo.
echo 🚀 Next Steps:
echo.
echo 1. Test with a single video:
echo    python test_single_video.py videos\w7.mp4
echo.
echo 2. Process all videos:
echo    python process_all_videos.py
echo.
echo 3. Use the web interface:
echo    http://localhost:3000
echo.
echo 💡 Note: This installed CPU version of PyTorch
echo    For GPU support, install CUDA-enabled PyTorch separately
echo.
pause

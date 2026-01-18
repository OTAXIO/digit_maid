# digit_maid
## A maid on PC
The aim of this project is to create a virtual maid that can help you 
with various tasks on your computer, such as organizing files, 
managing schedules, and providing reminders.
## Environment Setup
python=3.10.19

requirements.txt
## 语音处理
SpeechRecognition==3.10.0      # 语音识别库
pyaudio==0.2.11                # 音频输入
pyttsx3==2.90                  # 离线TTS
vosk==0.3.45                   # 离线语音识别（可选）
whisper==1.1.10                # OpenAI Whisper（高精度）
openai-whisper                 # 官方版本

## 语音唤醒（关键词检测）
porcupine==3.0.2               # 离线唤醒词检测
pvcobra==1.2.0                 # 语音活动检测
webrtcvad==2.0.10              # VAD检测

## GUI和动画
PyQt5==5.15.9                  # 桌面GUI
PyQt5-Qt5==5.15.2
pygame==2.5.2                  # 2D动画和音效
opencv-python==4.8.1           # 图像处理

## 系统自动化
pyautogui==0.9.54              # 屏幕自动化
psutil==5.9.6                  # 系统监控
pygetwindow==0.0.9             # 窗口管理
keyboard==0.13.5               # 全局热键

## AI和图像识别
pytesseract==0.3.10            # OCR
pillow==10.0.0                 # 图像处理
paddlepaddle==2.5.0            # PaddleOCR（可选）
ultralytics==8.0.196           # YOLO物体检测

## 其他工具
numpy==1.24.3
requests==2.31.0
schedule==1.2.0                # 定时任务

## 当前实现功能 (Implemented Features)

### 1. 运行指南 (How to Run)
本阶段实现使用了 PyQt6，请确保安装以下依赖：
```bash
pip install PyQt6 Pillow pyautogui
```

运行程序：
```bash
python src/core/code.py
```

### 2. 功能说明
*   **可视化UI**: 使用 PyQt6 构建的无边框圆形桌宠，支持鼠标拖拽，带眨眼动画。
*   **右键菜单**: 集成了以下功能。
*   **桌面整理**: 扫描桌面文件，按 Images, Videos, Documents 等分类移动到相应文件夹。
*   **屏幕截图**: 截取当前屏幕并保存到 `resource/` 文件夹。
*   **打开软件**: 快速启动计算器、记事本等。
@echo off
chcp 65001 >nul
echo ==============================================
echo           项目启动脚本 (Windows)
echo ==============================================
echo.

:: 1. 创建虚拟环境
echo [1/3] 正在创建/初始化虚拟环境...
python -m venv venv

:: 2. 激活虚拟环境
echo [2/3] 正在激活虚拟环境...
call venv\Scripts\activate.bat

:: 3. 启动项目（后台运行，避免卡住打不开浏览器）
echo [3/3] 正在启动项目 app.py...
start /B python app.py

:: 等待2秒，让服务器先启动（可根据你的项目快慢调整）
timeout /t 2 /nobreak >nul

:: ====================== 打开URL ======================
echo.
echo [完成] 正在自动打开项目地址...
start http://127.0.0.1:5000
:: ======================================================

echo.
echo 项目已启动，浏览器已自动打开！
echo 按 Ctrl + C 停止项目
echo.
pause >nul
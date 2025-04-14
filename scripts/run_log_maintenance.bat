@echo off
echo 开始执行日志维护任务 - %date% %time%
cd /d %~dp0..
python scripts/log_manager.py
echo 日志维护任务完成 - %date% %time%

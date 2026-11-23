@echo off
chcp 65001 >nul
cd /d "%~dp0python"
echo LoRA pipeline - Mehdi Tariri
echo 1 Export dataset
echo 2 Train
echo 3 Merge
echo 4 Full pipeline (export+train+merge)
echo 0 Cancel
set /p c=Choice: 
if "%c%"=="1" python export_dataset.py --src ..\..\dataset --out ..\..\dataset\auto\alpaca.jsonl
if "%c%"=="2" python train_lora.py --data ..\..\dataset\auto\alpaca.jsonl --out ..\..\models\lora-out
if "%c%"=="3" python merge_lora.py --base Qwen/Qwen2.5-3B-Instruct --lora ..\..\models\lora-out --out ..\..\models\merged-hf
if "%c%"=="4" python lora_pipeline.py --base Qwen/Qwen2.5-3B-Instruct
echo.
echo GGUF convert: see docs\LORA_TO_GGUF.md
pause

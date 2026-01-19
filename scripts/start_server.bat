@echo off
echo Starting the Steam Game Recommender server...
cd ..
uv run uvicorn src.main:app --reload

REM tasklist | findstr "uvicorn"
REM taskkill /F /PID 28552
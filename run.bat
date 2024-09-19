@echo off

if not defined GEMINI_API_KEY (
	echo GEMINI_API_KEY not found from environment variables.
    set /p GEMINI_API_KEY=Please enter your Gemini AI key: 
    
    echo GEMINI_API_KEY has been set.
) else (
    echo GEMINI_API_KEY is already set.
)

REM Run your desired command here
echo Start the AI app

.\.venv\Scripts\python.exe scripts/main.py config.json
pause
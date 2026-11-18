@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating the project virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Could not create the environment. Install Python 3 and ensure the py launcher is available.
        pause
        exit /b 1
    )
)

echo Installing or checking pinned project packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Package installation failed. Review the message above and check your internet connection.
    pause
    exit /b 1
)

if not exist "data\app.db" (
    echo Creating the synthetic SQLite database...
    ".venv\Scripts\python.exe" generate_data.py
    if errorlevel 1 (
        echo Synthetic data generation failed.
        pause
        exit /b 1
    )
)

echo Running the automated checks...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 (
    echo Tests failed; the dashboard will not start.
    pause
    exit /b 1
)

echo Starting the dashboard at http://localhost:8502
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8502
pause

@echo off
:menu
echo User Management Menu
echo ---------------------
echo 1. List all user names under sounds/users
echo 2. Add a new user by running record_master_wav.py
echo 3. Delete a user
echo 4. Exit
echo.

set /p choice=Enter your choice (1-4): 

if "%choice%"=="1" goto list_users
if "%choice%"=="2" goto add_user
if "%choice%"=="3" goto delete_user
if "%choice%"=="4" goto end

echo Invalid choice. Please try again.
timeout /t 2 >nul
goto menu

:list_users
echo.
echo List of users:
for %%F in (sounds\users\*.wav) do echo %%~nF
goto menu

:add_user
echo.
echo Adding a new user...
.venv\Scripts\python scripts/record_master_wav.py
echo User added successfully.
goto menu

:delete_user
echo.
set /p username=Enter the name of the user to delete: 
if exist "sounds\users\%username%.wav" (
    del "sounds\users\%username%.wav"
    echo User %username% has been deleted.
) else (
    echo User %username% not found.
)
goto menu

:end
echo Goodbye!
exit
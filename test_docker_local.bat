@echo off
REM Test Docker build and Tor setup locally before deploying to Render (Windows)

echo ==========================================
echo Local Docker + Tor Test (Windows)
echo ==========================================

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo X Docker is not installed
    echo Install Docker Desktop from: https://www.docker.com/get-started
    pause
    exit /b 1
)

echo √ Docker is installed

REM Build the Docker image
echo.
echo Building Docker image...
docker build -t youtube-server-test .

if errorlevel 1 (
    echo X Docker build failed
    pause
    exit /b 1
)

echo √ Docker image built successfully

REM Run the container
echo.
echo Starting container...
docker run -d -p 8080:8080 --name youtube-server-test youtube-server-test

if errorlevel 1 (
    echo X Failed to start container
    pause
    exit /b 1
)

echo √ Container started

REM Wait for services to start
echo.
echo Waiting for Tor and server to start (30 seconds)...
timeout /t 30 /nobreak >nul

REM Test the server
echo.
echo Testing server endpoints...

REM Test 1: Ping
echo 1. Testing /ping...
curl -s http://localhost:8080/ping | findstr "pong" >nul
if errorlevel 1 (
    echo    X Server not responding
) else (
    echo    √ Server is responding
)

REM Test 2: Tor status
echo 2. Testing /tor_status...
curl -s http://localhost:8080/tor_status > tor_status_temp.json

findstr "\"tor_enabled\": true" tor_status_temp.json >nul
if errorlevel 1 (
    echo    X Tor is not enabled
) else (
    echo    √ Tor is enabled
)

findstr "\"is_tor_exit\": true" tor_status_temp.json >nul
if errorlevel 1 (
    echo    X Tor is not working
) else (
    echo    √ Tor is working!
    for /f "tokens=2 delims=:" %%a in ('findstr "exit_ip" tor_status_temp.json') do (
        echo    → Exit IP: %%a
    )
)

del tor_status_temp.json

REM Show logs
echo.
echo ==========================================
echo Container Logs (last 20 lines):
echo ==========================================
docker logs --tail 20 youtube-server-test

REM Cleanup prompt
echo.
echo ==========================================
echo Test complete!
echo ==========================================
echo.
echo To view full logs:
echo   docker logs youtube-server-test
echo.
echo To stop and remove container:
echo   docker stop youtube-server-test
echo   docker rm youtube-server-test
echo.
echo To remove image:
echo   docker rmi youtube-server-test
echo.

set /p cleanup="Stop and remove container now? (y/n): "
if /i "%cleanup%"=="y" (
    docker stop youtube-server-test
    docker rm youtube-server-test
    echo √ Container stopped and removed
)

pause

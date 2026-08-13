@echo off
REM 이 파일이 있는 폴더로 이동한 뒤 job_alert.py를 실행합니다.
REM 실행 결과(로그)는 같은 폴더의 job_alert.log 파일에 계속 쌓입니다.
cd /d "%~dp0"
python job_alert.py >> job_alert.log 2>&1

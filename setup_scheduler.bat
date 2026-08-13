@echo off
chcp 65001 >nul
set SCRIPT_DIR=%~dp0

echo ============================================================
echo  공공기관 채용정보 알림 - 자동 실행 등록
echo ============================================================
echo.
echo  오전 9시, 저녁 6시에 하루 2번 자동으로 실행되도록
echo  Windows 작업 스케줄러에 등록합니다.
echo.

schtasks /create /tn "JobAlert_Morning" /tr "\"%SCRIPT_DIR%run_job_alert.bat\"" /sc daily /st 09:00 /f
schtasks /create /tn "JobAlert_Evening" /tr "\"%SCRIPT_DIR%run_job_alert.bat\"" /sc daily /st 18:00 /f

echo.
echo ============================================================
echo  등록 완료! 이제부터 매일 09:00, 18:00에 자동 실행됩니다.
echo  (컴퓨터가 켜져 있어야 실행됩니다)
echo.
echo  등록된 작업은 Windows 검색창에 "작업 스케줄러"를 입력해서
echo  확인/수정/삭제할 수 있습니다. (이름: JobAlert_Morning, JobAlert_Evening)
echo ============================================================
echo.
pause

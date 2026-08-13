import json
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """GitHub Secrets의 JSON 문자열을 통해 Google Calendar API 서비스 객체를 생성합니다."""
    sa_key_str = os.environ.get('GCP_SA_KEY')
    if not sa_key_str:
        raise ValueError("GCP_SA_KEY 환경 변수가 설정되지 않았습니다.")

    sa_info = json.loads(sa_key_str)
    creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    return build('calendar', 'v3', credentials=creds)

def add_job_deadline_to_calendar(title, due_date, link_url=""):
    """
    공고 마감일을 구글 캘린더에 하루 종일(All-day) 이벤트로 등록합니다.
    :param title: 공고 제목 (예: '[한국전력공사] 채용공고')
    :param due_date: 마감 날짜 (형식: 'YYYY-MM-DD', 예: '2026-08-25')
    :param link_url: 공고 상세 URL
    """
    try:
        service = get_calendar_service()
        calendar_id = os.environ.get('CALENDAR_ID')
        
        if not calendar_id:
            raise ValueError("CALENDAR_ID 환경 변수가 설정되지 않았습니다.")

        # 구글 캘린더 이벤트 데이터 구성
        event = {
            'summary': f'[공고 마감] {title}',
            'description': f'공고 상세링크: {link_url}\n(자동화 시스템으로 등록된 일정입니다.)',
            'start': {
                'date': due_date,  # 하루 종일 일정
                'timeZone': 'Asia/Seoul',
            },
            'end': {
                'date': due_date,
                'timeZone': 'Asia/Seoul',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 24 * 60},      # 1일 전 알림
                    {'method': 'popup', 'minutes': 3 * 24 * 60},  # 3일 전 알림
                ],
            },
        }

        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"캘린더 등록 성공: {created_event.get('htmlLink')}")
        return created_event

    except Exception as e:
        print(f"구글 캘린더 등록 실패: {e}")
        return None

# -*- coding: utf-8 -*-
"""
채용공고 마감일 캘린더 동기화 모듈
====================================

이 파일이 하는 일:
  1. 이번 실행에서 조건(전산직 등)에 맞게 가져온 공고들의 마감일을 모아서
     달력 표준 형식인 .ics 파일 내용을 만듭니다.
  2. 이미 마감이 지난 공고는 자동으로 목록에서 빠집니다.
  3. 완성된 .ics 내용을 GitHub Gist에 업데이트합니다.

구글 캘린더 등에서 이 Gist의 raw 파일 주소를 "URL로 캘린더 구독" 해두면,
스크립트가 실행될 때마다(하루 2번) 캘린더가 자동으로 최신 상태로 갱신됩니다.

필요한 환경변수(GitHub Actions Secrets):
  - GIST_TOKEN : gist 쓰기 권한이 있는 GitHub Personal Access Token
  - GIST_ID    : 미리 만들어둔 Gist의 ID
둘 중 하나라도 없으면 캘린더 동기화는 조용히 건너뜁니다(에러 없이 스킵).
"""

import json
import os
from datetime import datetime, timedelta

import requests

CALENDAR_JOBS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calendar_jobs.json")
ICS_FILENAME = "job_deadlines.ics"


def load_calendar_jobs() -> dict:
    """캘린더에 올라가 있는(마감 안 지난) 공고 목록을 불러옵니다. {공고ID: {제목,기관,마감일,URL}}"""
    if not os.path.exists(CALENDAR_JOBS_FILE):
        return {}
    try:
        with open(CALENDAR_JOBS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_calendar_jobs(jobs: dict) -> None:
    with open(CALENDAR_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)


def update_calendar_jobs(existing: dict, filtered_jobs: list) -> dict:
    """
    - 마감일이 지난 공고는 목록에서 제거
    - 이번에 새로 가져온 공고들을 추가/갱신
    """
    today = datetime.now().strftime("%Y%m%d")

    # 마감 지난 것 제거
    updated = {
        job_id: info for job_id, info in existing.items()
        if info.get("deadline", "99999999") >= today
    }

    # 새로 가져온 공고 추가/갱신
    for job in filtered_jobs:
        job_id = str(job.get("recrutPblntSn"))
        deadline = job.get("pbancEndYmd", "")
        if not deadline or deadline < today:
            continue  # 마감일 정보 없거나 이미 지났으면 캘린더에 안 올림
        url = job.get("srcUrl", "")
        if url and not url.startswith("http"):
            url = "https://" + url
        updated[job_id] = {
            "title": job.get("recrutPbancTtl", "제목 없음"),
            "inst": job.get("instNm", ""),
            "deadline": deadline,
            "url": url,
        }

    return updated


def _escape_ics_text(text: str) -> str:
    """ICS 형식에서 특수문자(콤마, 세미콜론, 줄바꿈)를 이스케이프합니다."""
    return (
        text.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


def build_ics(jobs: dict) -> str:
    """공고 딕셔너리를 .ics(iCalendar) 텍스트로 변환합니다.
    각 공고는 마감일 하루짜리 종일 일정으로 등록됩니다."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//job-alert//KR",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:공공기관 채용공고 마감일",
    ]

    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    for job_id, info in jobs.items():
        deadline = info["deadline"]  # YYYYMMDD
        next_day = (datetime.strptime(deadline, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        title = _escape_ics_text(f"[마감] {info['title']}")
        desc_parts = [info.get("inst", "")]
        if info.get("url"):
            desc_parts.append(info["url"])
        description = _escape_ics_text(" - ".join(p for p in desc_parts if p))

        lines += [
            "BEGIN:VEVENT",
            f"UID:job-alert-{job_id}@job-alert",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;VALUE=DATE:{deadline}",
            f"DTEND;VALUE=DATE:{next_day}",
            f"SUMMARY:{title}",
            f"DESCRIPTION:{description}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def push_to_gist(ics_content: str) -> bool:
    """만들어진 .ics 내용을 GitHub Gist에 업데이트합니다."""
    token = os.environ.get("GIST_TOKEN")
    gist_id = os.environ.get("GIST_ID")

    if not token or not gist_id:
        print("[캘린더] GIST_TOKEN 또는 GIST_ID가 설정되지 않아 캘린더 동기화를 건너뜁니다.")
        return False

    url = f"https://api.github.com/gists/{gist_id}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {"files": {ICS_FILENAME: {"content": ics_content}}}

    try:
        resp = requests.patch(url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        print("[캘린더] Gist 업데이트 완료")
        return True
    except requests.RequestException as e:
        print(f"[캘린더] Gist 업데이트 실패: {e}")
        return False


def sync_calendar(filtered_jobs: list) -> None:
    """메인 스크립트에서 호출하는 진입점 함수."""
    existing = load_calendar_jobs()
    updated = update_calendar_jobs(existing, filtered_jobs)
    save_calendar_jobs(updated)

    ics_content = build_ics(updated)
    push_to_gist(ics_content)
    print(f"[캘린더] 현재 캘린더에 올라간 공고: {len(updated)}건")

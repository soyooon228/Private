#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공공기관 채용정보 자동 알림 프로그램 (v2 - 실제 API 스펙 반영)
================================================================

무엇을 하는 프로그램인가요?
  1. 공공데이터포털 "재정경제부_공공기관 채용정보 조회서비스" API를 호출해서
     현재 진행중인 채용공고 목록을 가져옵니다.
  2. config.py 의 필터(직무분야/지역/고용형태 등)로 좁힙니다.
  3. 이미 알림을 보낸 공고는 제외하고, "새로 올라온 공고"만 골라냅니다.
  4. 새 공고가 있으면 보기 좋게 정리해서 슬랙 채널로 메시지를 보냅니다.
  5. 보낸 공고 ID는 seen_jobs.json 에 저장해서 다음 실행 때 중복 알림을 막습니다.

사용법
------
   python job_alert.py

전체 설정은 config.py 에서 관리합니다.
"""

import json
import os
from datetime import datetime

import requests

import config

SEEN_JOBS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_jobs.json")


def load_seen_jobs() -> set:
    """이전에 알림을 보낸 공고 ID(recrutPblntSn) 목록을 불러옵니다."""
    if not os.path.exists(SEEN_JOBS_FILE):
        return set()
    try:
        with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, IOError):
        return set()


def save_seen_jobs(seen_ids: set) -> None:
    with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen_ids), f, ensure_ascii=False, indent=2)


def fetch_jobs() -> list:
    """API를 호출해서 채용공고 목록(딕셔너리 리스트)을 가져옵니다."""
    params = {
        "serviceKey": config.DATA_GO_KR_API_KEY,
        "resultType": "json",
        "pageNo": 1,
        "numOfRows": config.NUM_OF_ROWS,
        "ongoingYn": "Y",  # 현재 접수중인 공고만
    }
    # 선택적 서버측 필터 (config.py에서 값이 있을 때만 추가)
    for key in ("hireTypeLst", "recrutSe", "workRgnLst", "ncsCdLst", "acbgCondLst"):
        value = getattr(config, key, "")
        if value:
            params[key] = value

    try:
        resp = requests.get(config.API_ENDPOINT, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"[에러] API 호출 실패: {e}")
        return []
    except ValueError:
        print("[에러] 응답이 JSON 형식이 아닙니다:", resp.text[:500])
        return []

    if str(data.get("resultCode")) != "200":
        print(f"[에러] API 오류 ({data.get('resultCode')}): {data.get('resultMsg')}")
        return []

    return data.get("result", [])


def format_date(yyyymmdd: str) -> str:
    """'20260826' -> '2026.08.26' 형태로 변환."""
    if not yyyymmdd or len(yyyymmdd) != 8:
        return yyyymmdd or "-"
    return f"{yyyymmdd[:4]}.{yyyymmdd[4:6]}.{yyyymmdd[6:]}"


def matches_keywords(job: dict) -> bool:
    """config.py의 KEYWORDS 중 하나라도 제목/기관명에 포함되면 True.
    (서버 필터를 이미 거친 뒤 추가로 좁히는 용도. KEYWORDS가 비어있으면 전체 통과)"""
    if not config.KEYWORDS:
        return True
    text = f"{job.get('recrutPbancTtl', '')} {job.get('instNm', '')}".lower()
    return any(kw.lower() in text for kw in config.KEYWORDS)


def is_highlight_region(job: dict) -> bool:
    """config.py의 HIGHLIGHT_REGIONS에 해당하는 지역이면 True."""
    region = job.get("workRgnNmLst", "")
    return any(r in region for r in getattr(config, "HIGHLIGHT_REGIONS", []))


def build_slack_blocks(new_jobs: list) -> dict:
    """새 공고 목록을 슬랙 메시지 payload로 변환합니다.
    관심 지역(HIGHLIGHT_REGIONS) 공고는 📍 표시를 붙이고 목록 맨 위로 정렬합니다."""
    # 관심 지역 공고를 먼저, 나머지는 그 뒤에
    sorted_jobs = sorted(new_jobs, key=lambda j: not is_highlight_region(j))

    highlight_count = sum(1 for j in new_jobs if is_highlight_region(j))
    header = f"*🔔 새로운 공공기관 채용공고 {len(new_jobs)}건*"
    if highlight_count:
        header += f"  (📍 관심지역 {highlight_count}건 포함)"
    lines = [header, ""]

    for job in sorted_jobs:
        title = job.get("recrutPbancTtl", "제목 없음")
        inst = job.get("instNm", "기관명 없음")
        region = job.get("workRgnNmLst", "")
        hire_type = job.get("hireTypeNmLst", "")
        recrut_se = job.get("recrutSeNm", "")
        deadline = format_date(job.get("pbancEndYmd", ""))
        url = job.get("srcUrl", "")
        if url and not url.startswith("http"):
            url = "https://" + url

        meta_parts = [p for p in [region, hire_type, recrut_se] if p]
        meta = " · ".join(meta_parts)

        prefix = "📍 " if is_highlight_region(job) else "• "
        title_line = f"{prefix}*<{url}|{title}>*" if url else f"{prefix}*{title}*"
        lines.append(title_line)
        lines.append(f"   🏢 {inst}" + (f"  |  {meta}" if meta else ""))
        lines.append(f"   ⏰ 마감: {deadline}")
        lines.append("")

    return {"text": "\n".join(lines)}


def send_slack_message(new_jobs: list) -> None:
    payload = build_slack_blocks(new_jobs)
    try:
        resp = requests.post(config.SLACK_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        print(f"[알림] 슬랙 메시지 전송 완료 ({len(new_jobs)}건)")
    except requests.RequestException as e:
        print(f"[에러] 슬랙 전송 실패: {e}")


def send_no_new_jobs_message() -> None:
    """새 공고가 없을 때 짧게 '정상 확인됨' 메시지를 보냅니다."""
    now = datetime.now().strftime("%m/%d %H:%M")
    payload = {"text": f"✅ 채용정보 확인 완료 ({now}) — 새로운 전산직 공고 없음"}
    try:
        resp = requests.post(config.SLACK_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        print("[알림] '새 공고 없음' 확인 메시지 전송 완료")
    except requests.RequestException as e:
        print(f"[에러] 슬랙 전송 실패: {e}")


def main():
    print(f"[{datetime.now().isoformat(timespec='seconds')}] 채용정보 확인 시작")

    seen_ids = load_seen_jobs()
    all_jobs = fetch_jobs()

    if not all_jobs:
        print("가져온 공고가 없습니다. (조건에 맞는 공고가 없거나 API 설정을 확인해주세요)")
        return

    filtered = [j for j in all_jobs if matches_keywords(j)]
    new_jobs = [
        j for j in filtered
        if str(j.get("recrutPblntSn")) not in seen_ids
    ]

    print(f"전체 {len(all_jobs)}건 중 키워드 일치 {len(filtered)}건, 신규 {len(new_jobs)}건")

    if new_jobs:
        send_slack_message(new_jobs)
        seen_ids.update(str(j.get("recrutPblntSn")) for j in new_jobs)
        save_seen_jobs(seen_ids)
    else:
        print("새로운 공고가 없습니다.")
        send_no_new_jobs_message()


if __name__ == "__main__":
    main()

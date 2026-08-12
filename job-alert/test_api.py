# -*- coding: utf-8 -*-
"""
API 연결 테스트 (v2 - 정확한 스펙 반영)
=========================================
공공기관 채용정보 API의 실제 스펙을 확인했습니다:
  - 엔드포인트: https://apis.data.go.kr/1051000/recruitment/list  (끝에 /list 필요!)
  - 필수 파라미터: serviceKey, resultType=json
  - 응답 구조: { resultCode, resultMsg, totalCount, result: [ ... ] }

사용법:
    python test_api.py
"""

import json
import requests
import config

params = {
    "serviceKey": config.DATA_GO_KR_API_KEY,
    "resultType": "json",
    "pageNo": 1,
    "numOfRows": 5,   # 테스트니까 5건만
}

print("요청 URL:", config.API_ENDPOINT)
print("요청 파라미터:", {**params, "serviceKey": params["serviceKey"][:10] + "..."})
print("-" * 60)

try:
    resp = requests.get(config.API_ENDPOINT, params=params, timeout=15)
    print("상태 코드:", resp.status_code)
    print()
    try:
        data = resp.json()
        print("resultCode:", data.get("resultCode"))
        print("resultMsg:", data.get("resultMsg"))
        print("totalCount:", data.get("totalCount"))
        print()
        print("샘플 데이터(첫 번째 항목):")
        results = data.get("result", [])
        if results:
            print(json.dumps(results[0], ensure_ascii=False, indent=2))
        else:
            print("(결과 없음)")
    except ValueError:
        print("JSON 파싱 실패. 원본 응답(앞 1500자):")
        print(resp.text[:1500])
except requests.RequestException as e:
    print(f"[에러] 요청 실패: {e}")

print("\n\n위 출력 내용을 그대로 복사해서 알려주세요.")

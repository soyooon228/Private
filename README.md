# 공공기관 채용정보 슬랙 알림 봇

사이트를 직접 열지 않아도, 원하는 직종의 새 채용공고가 올라오면 슬랙으로 알림을 받습니다.

## 1. 설치

```bash
pip install -r requirements.txt
```

## 2. 설정 (config.py)

| 항목 | 설명 | 어디서 발급하나요 |
|---|---|---|
| `DATA_GO_KR_API_KEY` | 채용정보 API 인증키 | [공공데이터포털](https://www.data.go.kr/data/15125273/openapi.do) → 활용신청 |
| `API_ENDPOINT` | API 호출 주소 | 위 페이지의 "상세설명"/Swagger 문서에서 정확한 주소 확인 |
| `SLACK_WEBHOOK_URL` | 슬랙으로 메시지를 보낼 웹훅 주소 | [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks) |
| `KEYWORDS` | 알림 받고 싶은 직종/기관명 키워드 목록 | 직접 입력 (예: `["전산", "IT"]`) |

⚠️ **중요**: 공공데이터포털 API는 승인 후 실제 응답 구조(JSON 필드명)를 확인해야
`job_alert.py`의 `parse_response()` 함수를 정확히 맞출 수 있습니다.
API 활용신청이 승인되면 상세페이지의 "미리보기" 또는 Swagger 문서를 캡처해서
알려주시면 정확한 필드명으로 코드를 바로 수정해드릴게요.

## 3. 실행해보기

```bash
python job_alert.py
```

새 공고가 있으면 콘솔에 로그가 뜨고 슬랙으로 메시지가 전송됩니다.
처음 실행 시에는 `seen_jobs.json`이 없어서 현재 조건에 맞는 모든 공고가
"신규"로 잡힐 수 있어요. 한 번 정상 작동을 확인한 뒤부터는 새로 올라온 공고만
알림이 옵니다.

## 4. 자동으로 주기 실행하기 (예약 실행)

### Windows — 작업 스케줄러
1. 시작 메뉴에서 "작업 스케줄러" 실행
2. "기본 작업 만들기" 클릭
3. 트리거: 매일, 원하는 시간(예: 오전 9시, 오후 6시) 설정
4. 작업: "프로그램 시작"
   - 프로그램/스크립트: `python`의 전체 경로 (예: `C:\Users\사용자명\AppData\Local\Programs\Python\Python312\python.exe`)
   - 인수 추가: `job_alert.py`
   - 시작 위치: 이 스크립트가 있는 폴더 경로 (예: `C:\Users\사용자명\job-alert`)
5. 완료 후 우클릭 → 실행으로 테스트

### macOS / Linux — cron
터미널에서:
```bash
crontab -e
```
아래 줄 추가 (매일 오전 9시, 오후 6시에 실행 예시):
```
0 9,18 * * * cd /본인_경로/job-alert && /usr/bin/python3 job_alert.py >> job_alert.log 2>&1
```

## 5. 동작 원리 요약

1. `job_alert.py`가 공공데이터포털 API를 호출해서 최신 채용공고 목록을 받아옵니다.
2. `config.py`의 `KEYWORDS`로 필터링합니다.
3. `seen_jobs.json`에 없는(=새로운) 공고만 골라냅니다.
4. 새 공고가 있으면 슬랙 웹훅으로 메시지를 보냅니다.
5. 보낸 공고 ID를 `seen_jobs.json`에 저장해 다음 실행 때 중복 알림을 막습니다.

## 문제 해결

- **"API 설정을 확인해주세요"라고 뜰 때**: `API_ENDPOINT`나 `DATA_GO_KR_API_KEY`가
  틀렸거나, 아직 활용신청이 승인되지 않았을 수 있어요 (보통 몇 분~반나절 소요).
- **응답 구조 에러가 뜰 때**: 콘솔에 출력되는 실제 JSON을 보고
  `parse_response()` 함수의 필드명(`pblancNm`, `insttNm` 등)을 실제 응답에 맞게 바꿔주세요.
- **슬랙 메시지가 안 올 때**: 웹훅 URL이 맞는지, 해당 슬랙 앱이 채널에 추가되어 있는지 확인하세요.

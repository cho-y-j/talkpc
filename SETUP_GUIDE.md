# TalkPC SaaS 플랫폼 - 테스트 가이드

## 프로젝트 구조

```
talk/
├── main.py                  # 클라이언트 앱 진입점 (--saas 옵션)
├── core/
│   ├── api_client.py        # SaaS 서버 HTTP 클라이언트
│   ├── orchestrator.py      # 매크로 오케스트레이터
│   ├── contact_manager.py   # 로컬 연락처 관리
│   └── sejong_sender.py     # 세종텔레콤 직접 발송 (로컬용)
├── ui/
│   ├── app.py               # 메인 앱 (SaaS/로컬 듀얼모드)
│   ├── components/sidebar.py
│   └── pages/
│       ├── login_page.py    # SaaS 로그인/회원가입
│       ├── dashboard_page.py
│       ├── contact_page.py  # 연락처 (API/로컬 듀얼)
│       ├── send_page.py     # 발송 (API/매크로 듀얼)
│       ├── usage_page.py    # 사용량/잔액 (SaaS 전용)
│       ├── template_page.py
│       └── settings_page.py
├── server/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI 앱
│       ├── config.py        # 환경변수 (DB URL, JWT 시크릿)
│       ├── database.py      # SQLAlchemy async engine
│       ├── db/init.sql      # DDL + 보안 테이블 + 관리자 시드
│       ├── middleware/auth.py
│       ├── models/          # user, credit, contact, template, send_log, device
│       ├── schemas/         # Pydantic 요청/응답
│       ├── routers/         # auth, account, contacts, templates, send, usage, admin, web_admin
│       ├── services/        # auth_service, credit_service, send_service, stats_service, security_service
│       └── templates/admin/ # 관리자 웹 (Jinja2 + Bootstrap 5)
└── MessagingAgent_v1.7.1.4/ # 세종텔레콤 Java 에이전트
    └── cnf/msg.cfg          # GW 접속 설정
```

---

## 1. 로컬 개발 환경 세팅 (Mac)

### 1-1. Python 가상환경

```bash
cd /Users/jojo/pro/talk
python3.13 -m venv .venv        # 이미 생성됨
source .venv/bin/activate
pip install -r requirements.txt  # 클라이언트 의존성
```

### 1-2. PostgreSQL (로컬)

```bash
# Homebrew로 설치된 PostgreSQL 사용 중
# DB: talkpc, User: jojo (비밀번호 없음)

# 테이블 초기화 (필요 시)
psql talkpc < server/app/db/init.sql
```

### 1-3. FastAPI 서버 실행 (로컬)

```bash
cd /Users/jojo/pro/talk/server
source ../.venv/bin/activate

# 서버 의존성 설치 (최초 1회)
pip install -r requirements.txt
pip install bcrypt==4.0.1       # bcrypt 5.x 호환 문제 방지

# 환경변수 (로컬 PostgreSQL용)
export DATABASE_URL="postgresql+asyncpg://jojo:@localhost:5432/talkpc"
export JWT_SECRET="change-this-secret-in-production"

# 서버 시작
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

서버 확인:
- API 문서: http://localhost:8000/docs
- 관리자 웹: http://localhost:8000/web/admin/login

### 1-4. 클라이언트 앱 실행

```bash
cd /Users/jojo/pro/talk
source .venv/bin/activate

# 로컬 모드 (카카오톡 매크로만)
python main.py

# SaaS 모드 (서버 연동)
python main.py --saas

# SaaS 모드 + 서버 주소 지정
python main.py --saas --server http://localhost:8000
```

---

## 2. Docker 환경 (협업자용)

### 2-1. Docker로 서버 시작

```bash
cd /Users/jojo/pro/talk/server

# API + PostgreSQL만 시작
docker-compose up -d

# MessagingAgent 포함 시작 (세종텔레콤 IP 승인 후)
docker-compose up -d --profile with-agent

# 로그 확인
docker-compose logs -f api
docker-compose logs -f postgres

# 종료
docker-compose down

# DB 초기화 (볼륨 삭제)
docker-compose down -v
```

### 2-2. Docker 포트 매핑

| 서비스 | 컨테이너 포트 | 호스트 포트 | 비고 |
|--------|-------------|------------|------|
| postgres | 5432 | 15432 | 로컬 PG와 충돌 방지 |
| api | 8000 | 8000 | FastAPI |
| messaging-agent | - | - | 외부 포트 없음 (DB만 접근) |

### 2-3. Docker 환경 DB 접속

```bash
# psql로 Docker DB 접속
psql -h localhost -p 15432 -U talkpc -d talkpc
# 비밀번호: talkpc1234
```

---

## 3. 테스트 계정

### 로컬 PostgreSQL (개발용)
| 구분 | 아이디 | 비밀번호 | 역할 | 잔액 |
|------|--------|---------|------|------|
| 관리자 | admin | admin1234 | admin | 0원 |
| 테스트 | testuser | test1234 | user | 10,000원 |

### Docker 환경
| 구분 | 아이디 | 비밀번호 | 역할 |
|------|--------|---------|------|
| 관리자 | admin | admin1234 | admin |
- Docker 환경은 init.sql에서 admin 계정 자동 생성
- 일반 사용자는 회원가입으로 생성

---

## 4. API 엔드포인트 요약

모든 API는 `/api` 프리픽스. 인증 필요한 API는 `Authorization: Bearer <JWT>` 헤더 필요.

### 인증
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | /api/auth/register | 회원가입 → JWT 반환 (device_id 포함 시 첫 기기 자동 승인) |
| POST | /api/auth/login | 로그인 → JWT 또는 기기 인증 요청 반환 |
| POST | /api/auth/verify-device | 기기 인증 코드 확인 → JWT 반환 |
| POST | /api/auth/resend-code | 인증 코드 재발송 |
| POST | /api/auth/change-password | 비밀번호 변경 |

### 계정
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | /api/account/me | 내 정보 + 잔액 |
| PUT | /api/account/me | 정보 수정 |

### 연락처
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | /api/contacts | 목록 (검색/필터) |
| POST | /api/contacts | 추가 |
| PUT | /api/contacts/{id} | 수정 |
| DELETE | /api/contacts/{id} | 삭제 |
| POST | /api/contacts/import | 엑셀 업로드 |
| GET | /api/contacts/export | 엑셀 다운로드 |

### 템플릿
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | /api/templates | 목록 |
| POST | /api/templates | 추가 |
| PUT | /api/templates/{id} | 수정 |
| DELETE | /api/templates/{id} | 삭제 |

### 발송
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | /api/send/sms | SMS/LMS 발송 (한도 체크 포함) |
| POST | /api/send/alimtalk | 알림톡 발송 (한도 체크 포함) |
| POST | /api/send/batch | 다건 발송 |
| GET | /api/send/history | 발송 이력 (페이징) |

### 사용량
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | /api/usage/daily | 오늘 사용량 + 잔액 |
| GET | /api/usage/monthly | 이번 달 사용량 |
| GET | /api/usage/stats | 전체 통계 |

### 관리자 (role=admin 필수)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | /api/admin/users | 전체 회원 목록 (잔액, 한도, 잠금 상태 포함) |
| GET | /api/admin/users/{id} | 회원 상세 (기기 목록, 보안 로그 포함) |
| PUT | /api/admin/users/{id} | 활성화/차단/역할/한도/시간/잠금 변경 |
| POST | /api/admin/users/{id}/credit | 크레딧 부여/차감 |
| POST | /api/admin/users/{id}/approve-device | 기기 승인 (관리자) |
| DELETE | /api/admin/users/{id}/devices/{device_id} | 기기 삭제 (분실 대응) |
| GET | /api/admin/stats | 전체 통계 |
| GET | /api/admin/send-logs | 전체 발송 로그 |
| GET | /api/admin/security-logs | 전체 보안 로그 |

### 관리자 웹 페이지
| 경로 | 설명 |
|------|------|
| /web/admin/login | 로그인 |
| /web/admin/ | 대시보드 |
| /web/admin/users | 회원 관리 |
| /web/admin/users/{id} | 회원 상세 |
| /web/admin/send-logs | 발송 로그 |

---

## 5. 과금 체계

| 메시지 유형 | 단가 |
|------------|------|
| SMS (90바이트 이하) | 8원/건 |
| LMS (90바이트 초과) | 25원/건 |
| 알림톡 | 7원/건 |

- 잔액 부족 시 발송 불가 (402 에러)
- 관리자가 크레딧 부여 가능 (관리자 웹 → 회원 상세 → 충전)

---

## 6. 보안 기능

### 6-0. API 키 인증 (프로그램 내장)

모든 `/api` 요청에 `X-API-Key` 헤더가 필수입니다. 키가 없거나 틀리면 403 차단.

- **서버**: `API_SECRET_KEY` 환경변수로 설정 (기본: `tpc-k8x2m9vQfR7wLpN3jY6sT0dA4hE1cU5b`)
- **클라이언트 프로그램**: `core/api_client.py`에 키 내장 → 프로그램 없이는 API 호출 불가
- **관리자 웹**: HTML 내 JS에 키 포함

```bash
# API 키 없이 호출 → 403 차단
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin1234"}'
# → {"detail": "유효하지 않은 API 키입니다"}

# API 키 포함 → 정상
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tpc-k8x2m9vQfR7wLpN3jY6sT0dA4hE1cU5b" \
  -d '{"username":"admin","password":"admin1234"}'
```

> **운영 시 변경**: 배포 전 `API_SECRET_KEY` 환경변수를 새 값으로 교체하고, 클라이언트 `_API_KEY`도 동일하게 변경 후 빌드.

### 6-1. 발송 한도 + 자동 차단

사용자별로 관리자가 설정하는 발송 한도:

| 설정 | 기본값 | 설명 |
|------|--------|------|
| hourly_limit | 200건 | 시간당 최대 발송 건수 |
| daily_limit | 1000건 | 일일 최대 발송 건수 |

- 한도 초과 시 → 계정 자동 잠금 (`is_locked = true`)
- 잠금된 계정은 로그인 불가 + 발송 불가
- 관리자만 잠금 해제 가능 (`PUT /api/admin/users/{id}` → `is_locked: false`)
- 모든 잠금 이벤트는 보안 로그에 기록

```bash
# 관리자: 사용자 한도 설정
curl -X PUT http://localhost:8000/api/admin/users/2 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"hourly_limit": 100, "daily_limit": 500}'

# 관리자: 잠금 해제
curl -X PUT http://localhost:8000/api/admin/users/2 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_locked": false}'
```

### 6-2. 기기 등록 + 이메일 인증

새 기기에서 로그인 시 인증 절차:

```
1. 로그인 요청 (device_id + device_name 포함)
2. 서버가 기기 확인
   ├── 승인된 기기 → JWT 토큰 발급
   ├── 새 기기 + 이메일 등록됨 → 이메일로 6자리 인증 코드 발송
   └── 새 기기 + 이메일 없음 → 관리자 승인 대기
3. 인증 코드 입력 (POST /api/auth/verify-device)
4. 인증 성공 → JWT 토큰 발급 + 기기 승인 완료
```

- 회원가입 시 첫 기기는 자동 승인
- 인증 코드 유효시간: 10분
- 관리자가 기기 승인/삭제 가능 (분실/탈취 대응)

```bash
# 새 기기로 로그인
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test1234","device_id":"NEW-PC-001","device_name":"새 노트북"}'
# → {"requires_verify": true, "verify_method": "email", ...}

# 인증 코드 입력
curl -X POST http://localhost:8000/api/auth/verify-device \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","device_id":"NEW-PC-001","code":"123456"}'
# → {"access_token": "...", ...}

# 관리자: 기기 승인
curl -X POST "http://localhost:8000/api/admin/users/2/approve-device?device_id=3" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 관리자: 기기 삭제 (분실 대응)
curl -X DELETE http://localhost:8000/api/admin/users/2/devices/3 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 6-3. 야간 발송 차단

사용자별 발송 가능 시간대 설정:

| 설정 | 기본값 | 설명 |
|------|--------|------|
| send_start_hour | 8 | 발송 시작 시간 (8시) |
| send_end_hour | 21 | 발송 종료 시간 (21시) |

- 허용 시간 외 발송 시도 → 403 에러
- 관리자가 사용자별로 개별 설정 가능

```bash
# 관리자: 발송 시간 설정 (9시~18시만 허용)
curl -X PUT http://localhost:8000/api/admin/users/2 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"send_start_hour": 9, "send_end_hour": 18}'
```

### 6-4. 보안 로그

모든 보안 이벤트가 IP 주소와 함께 기록됩니다:

| 이벤트 | 설명 |
|--------|------|
| register | 회원가입 |
| login | 로그인 성공 |
| login_fail | 로그인 실패 (비밀번호 오류) |
| new_device | 새 기기 등록 요청 |
| device_verified | 기기 인증 완료 |
| verify_fail | 기기 인증 실패 |
| auto_lock | 한도 초과 자동 잠금 |
| admin_unlock | 관리자 잠금 해제 |
| admin_lock | 관리자 수동 잠금 |
| admin_device_approve | 관리자 기기 승인 |
| admin_device_delete | 관리자 기기 삭제 |
| password_change | 비밀번호 변경 |

```bash
# 관리자: 보안 로그 조회
curl http://localhost:8000/api/admin/security-logs \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 6-5. 해킹 대응 시나리오

**해커가 크레딧 도용 대량 발송 시도 시:**
1. 새 기기에서 로그인 → 이메일 인증 필요 (기기 인증 차단)
2. 기존 기기 탈취하더라도 → 시간당/일일 한도 초과 시 자동 잠금
3. 야간 발송 시도 → 시간대 차단
4. 모든 시도가 보안 로그에 IP와 함께 기록 → 관리자 추적 가능

---

## 7. 동작 모드

### SaaS 모드 (`python main.py --saas`)
1. 로그인 화면 표시
2. 로그인 성공 → 메인 화면 (대시보드, 연락처, 발송, 사용량)
3. 연락처/템플릿 → 서버 API로 CRUD
4. 발송 → 서버에서 한도 체크 + msg_queue INSERT + 크레딧 차감
5. MessagingAgent가 msg_queue 폴링 → 세종텔레콤 GW로 전송
6. 카카오톡 매크로 기능도 사용 가능 (대시보드 빠른 실행)

### 로컬 모드 (`python main.py`)
1. 로그인 없이 바로 메인 화면
2. 연락처 → 로컬 JSON 파일
3. 발송 → pyautogui 카카오톡 매크로
4. 서버 불필요

---

## 8. 발송 플로우 (SaaS)

```
클라이언트 → POST /api/send/sms → 서버
  1. 계정 잠금 확인
  2. 야간 발송 차단 확인
  3. 시간당/일일 한도 확인 (초과 시 자동 잠금)
  4. 잔액 확인 (credits 합계 >= 비용?)
  5. msg_queue INSERT (RETURNING mseq)
  6. credits 차감 INSERT (type='use')
  7. send_logs INSERT
  → 모두 1개 트랜잭션

MessagingAgent (Java)
  1. msg_queue에서 stat='0' 레코드 SELECT
  2. 세종텔레콤 GW(202.30.241.23)로 전송
  3. stat='2'(성공) 또는 stat='3'(실패) 업데이트
  4. msg_result_yyyymm 테이블로 이동
```

---

## 9. MessagingAgent 설정

파일: `MessagingAgent_v1.7.1.4/cnf/msg.cfg`

```ini
[host]
host-name = 202.30.241.23      # 세종텔레콤 GW

[bindInfo1]
bind-cid1  = 90568N0568        # 계약 CID
bind-id1   = Cho2239148        # 접속 ID
bind-passwd1 = cho16133        # 접속 비밀번호

[dbms]
dbms-type = postgres
dbms-host = localhost           # Docker에서는 'postgres'
dbms-port = 5432
dbms-name = talkpc
dbms-user = jojo               # Docker에서는 'talkpc'
dbms-passwd =                   # Docker에서는 'talkpc1234'
```

**주의:** 세종텔레콤 GW는 IP 화이트리스트 방식. 현재 개발 IP 승인 대기 중.

---

## 10. DB 테이블 구조

| 테이블 | 용도 |
|--------|------|
| users | 사용자 (한도, 잠금, 발송 시간 설정 포함) |
| credits | 크레딧 내역 (충전/사용/보너스) |
| contacts | 연락처 (사용자별 격리) |
| templates | 메시지 템플릿 (JSONB) |
| send_logs | 발송 로그 |
| devices | 등록 기기 (인증 상태) |
| security_logs | 보안 이벤트 로그 (IP 포함) |
| msg_queue | 세종텔레콤 발송 큐 |
| msg_result_yyyymm | 발송 결과 (월별) |
| msg_queue_block | 차단 번호 |

---

## 11. 알려진 이슈

1. **세종텔레콤 IP 미승인**: GW 접속 불가 → MessagingAgent 발송 실패. IP 승인 후 해결 예정.
2. **bcrypt 버전**: bcrypt 5.x와 passlib 비호환. 반드시 `bcrypt==4.0.1` 사용.
3. **Python 버전**: macOS에서 Python 3.13 필요 (시스템 Python 3.9.6은 Tkinter 호환 문제).
4. **Tkinter 색상**: `#ffffff99` 같은 알파 채널 색상 사용 불가. 6자리 hex만 사용.
5. **msg_result 테이블**: `msg_result_yyyymm` 형식으로 매월 테이블 생성 필요. 현재 `msg_result_202603`만 존재.
6. **이메일 발송**: 기기 인증 이메일은 현재 서버 로그에 출력 (실제 SMTP/SES 연동 필요).

---

## 12. curl 테스트 예시

```bash
# 회원가입 (기기 포함)
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test1234","name":"테스트","email":"test@example.com","device_id":"MY-PC-001","device_name":"내 PC"}'

# 로그인 (기기 인증 포함)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test1234","device_id":"MY-PC-001","device_name":"내 PC"}'

# 로그인 (기기 없이 - 기존 호환) ※ 모든 /api 호출에 X-API-Key 필수
API_KEY="tpc-k8x2m9vQfR7wLpN3jY6sT0dA4hE1cU5b"
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"username":"admin","password":"admin1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 내 정보
curl -H "Authorization: Bearer $TOKEN" -H "X-API-Key: $API_KEY" http://localhost:8000/api/account/me

# 연락처 추가
curl -X POST http://localhost:8000/api/contacts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"홍길동","phone":"01012345678","category":"customer"}'

# 크레딧 부여 (관리자)
curl -X POST http://localhost:8000/api/admin/users/2/credit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount":50000,"description":"테스트 크레딧"}'

# SMS 발송
curl -X POST http://localhost:8000/api/send/sms \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"contact_ids":[1],"message":"테스트 메시지","subject":"알림"}'

# 사용량 확인
curl -H "Authorization: Bearer $TOKEN" -H "X-API-Key: $API_KEY" http://localhost:8000/api/usage/daily

# 보안 로그 (관리자)
curl -H "Authorization: Bearer $TOKEN" -H "X-API-Key: $API_KEY" http://localhost:8000/api/admin/security-logs

# 사용자 한도 설정 (관리자)
curl -X PUT http://localhost:8000/api/admin/users/2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"hourly_limit":100,"daily_limit":500,"send_start_hour":9,"send_end_hour":18}'
```

---

## 13. 향후 작업

- [ ] 세종텔레콤 IP 승인 → 실제 발송 테스트
- [ ] 이메일 발송 서비스 연동 (SMTP 또는 AWS SES) → 기기 인증 이메일 실제 발송
- [ ] AWS 인스턴스 생성 + Docker 배포
- [ ] PyInstaller로 .exe 빌드 (Windows/Mac)
- [ ] 클라이언트 앱에 기기 인증 UI 연동 (login_page.py)
- [ ] 관리자 웹에 보안 로그/기기 관리 페이지 추가
- [ ] 자동결제 연동 (향후)
- [ ] msg_result 테이블 월별 자동 생성

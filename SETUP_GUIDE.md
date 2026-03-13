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
│       ├── db/init.sql      # DDL + 관리자 시드
│       ├── middleware/auth.py
│       ├── models/          # user, credit, contact, template, send_log
│       ├── schemas/         # Pydantic 요청/응답
│       ├── routers/         # auth, account, contacts, templates, send, usage, admin, web_admin
│       ├── services/        # auth_service, credit_service, send_service, stats_service
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
| POST | /api/auth/register | 회원가입 → JWT 반환 |
| POST | /api/auth/login | 로그인 → JWT 반환 |
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
| POST | /api/send/sms | SMS/LMS 발송 |
| POST | /api/send/alimtalk | 알림톡 발송 |
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
| GET | /api/admin/users | 전체 회원 목록 |
| GET | /api/admin/users/{id} | 회원 상세 |
| PUT | /api/admin/users/{id} | 활성화/차단/역할 변경 |
| POST | /api/admin/users/{id}/credit | 크레딧 부여/차감 |
| GET | /api/admin/stats | 전체 통계 |
| GET | /api/admin/send-logs | 전체 발송 로그 |

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

## 6. 동작 모드

### SaaS 모드 (`python main.py --saas`)
1. 로그인 화면 표시
2. 로그인 성공 → 메인 화면 (대시보드, 연락처, 발송, 사용량)
3. 연락처/템플릿 → 서버 API로 CRUD
4. 발송 → 서버에서 msg_queue INSERT + 크레딧 차감
5. MessagingAgent가 msg_queue 폴링 → 세종텔레콤 GW로 전송
6. 카카오톡 매크로 기능도 사용 가능 (대시보드 빠른 실행)

### 로컬 모드 (`python main.py`)
1. 로그인 없이 바로 메인 화면
2. 연락처 → 로컬 JSON 파일
3. 발송 → pyautogui 카카오톡 매크로
4. 서버 불필요

---

## 7. 발송 플로우 (SaaS)

```
클라이언트 → POST /api/send/sms → 서버
  1. 잔액 확인 (credits 합계 >= 비용?)
  2. msg_queue INSERT (RETURNING mseq)
  3. credits 차감 INSERT (type='use')
  4. send_logs INSERT
  → 모두 1개 트랜잭션

MessagingAgent (Java)
  1. msg_queue에서 stat='0' 레코드 SELECT
  2. 세종텔레콤 GW(202.30.241.23)로 전송
  3. stat='2'(성공) 또는 stat='3'(실패) 업데이트
  4. msg_result_yyyymm 테이블로 이동
```

---

## 8. MessagingAgent 설정

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

## 9. 알려진 이슈

1. **세종텔레콤 IP 미승인**: GW 접속 불가 → MessagingAgent 발송 실패. IP 승인 후 해결 예정.
2. **bcrypt 버전**: bcrypt 5.x와 passlib 비호환. 반드시 `bcrypt==4.0.1` 사용.
3. **Python 버전**: macOS에서 Python 3.13 필요 (시스템 Python 3.9.6은 Tkinter 호환 문제).
4. **Tkinter 색상**: `#ffffff99` 같은 알파 채널 색상 사용 불가. 6자리 hex만 사용.
5. **msg_result 테이블**: `msg_result_yyyymm` 형식으로 매월 테이블 생성 필요. 현재 `msg_result_202603`만 존재.

---

## 10. curl 테스트 예시

```bash
# 회원가입
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test1234","name":"테스트"}'

# 로그인
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 내 정보
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/account/me

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
  -d '{"contacts":[{"name":"홍길동","phone":"01012345678"}],"message":"테스트 메시지","callback":"01000000000"}'

# 사용량 확인
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/usage/daily
```

---

## 11. 향후 작업

- [ ] 세종텔레콤 IP 승인 → 실제 발송 테스트
- [ ] AWS 인스턴스 생성 + Docker 배포
- [ ] PyInstaller로 .exe 빌드 (Windows/Mac)
- [ ] 자동결제 연동 (향후)
- [ ] msg_result 테이블 월별 자동 생성

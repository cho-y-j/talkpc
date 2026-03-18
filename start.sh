#!/bin/bash
# ══════════════════════════════════════
#  TalkPC 자동 시작 스크립트
# ══════════════════════════════════════

set -e
cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  TalkPC 시작"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. .env 파일 확인
if [ ! -f "server/.env" ]; then
    echo -e "${RED}[오류] server/.env 파일이 없습니다.${NC}"
    echo "  server/.env.example 을 복사하여 설정하세요."
    exit 1
fi
echo -e "${GREEN}[OK]${NC} 환경변수 파일 확인"

# 2. Docker 실행 확인
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}[오류] Docker가 실행되지 않았습니다. Docker Desktop을 시작하세요.${NC}"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Docker 실행 중"

# 3. Docker Compose 시작 (SaaS 서버 + DB)
echo -e "${YELLOW}[...] Docker 컨테이너 시작 중...${NC}"
cd server
docker-compose up -d --build 2>&1 | tail -3
cd ..
echo -e "${GREEN}[OK]${NC} SaaS 서버 시작 (http://localhost:8000)"

# 4. 서버 헬스체크 (최대 15초 대기)
echo -e "${YELLOW}[...] 서버 응답 대기 중...${NC}"
for i in $(seq 1 15); do
    if curl -s -o /dev/null http://localhost:8000/health 2>/dev/null; then
        echo -e "${GREEN}[OK]${NC} 서버 정상 응답"
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo -e "${RED}[경고] 서버 응답 지연 - docker-compose logs api 로 확인하세요${NC}"
    fi
    sleep 1
done

# 5. 모드 선택
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  실행 모드 선택"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  1) SaaS 모드 (서버 연동)"
echo "  2) 로컬 모드 (오토마우스만)"
echo "  3) 서버만 (클라이언트 실행 안함)"
echo ""
read -p "선택 [1/2/3]: " MODE

case $MODE in
    1)
        echo -e "${GREEN}[시작]${NC} SaaS 클라이언트 실행..."
        source .venv/bin/activate
        python main.py --saas --server http://localhost:8000 &
        ;;
    2)
        echo -e "${GREEN}[시작]${NC} 로컬 클라이언트 실행..."
        source .venv/bin/activate
        python main.py &
        ;;
    3)
        echo -e "${GREEN}[완료]${NC} 서버만 시작됨"
        ;;
    *)
        echo -e "${YELLOW}잘못된 선택. 서버만 시작됩니다.${NC}"
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  ${GREEN}관리자 웹:${NC} http://localhost:8000/web/admin/login"
echo -e "  ${GREEN}API 문서:${NC}  http://localhost:8000/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

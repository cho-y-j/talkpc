"""
TalkPC - Auto Messenger
========================
카카오톡/알림톡/SMS 자동 메시지 발송 프로그램

동작 모드:
- SaaS 모드 (--saas): 서버 연결, 로그인 필수, API 기반 연락처/발송/과금
- 로컬 모드 (기본): 서버 불필요, 기존 카카오톡 봇 발송

사용법:
  python main.py              # 로컬 모드
  python main.py --saas       # SaaS 모드 (서버 연결)
  python main.py --saas --server http://your-server:8000
"""

import sys
import os
import argparse
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)


def check_dependencies():
    """의존성 확인"""
    missing = []
    for pkg in ["customtkinter", "pyautogui", "pytesseract", "PIL", "openpyxl"]:
        try:
            __import__(pkg)
        except ImportError:
            name_map = {"PIL": "Pillow"}
            missing.append(name_map.get(pkg, pkg))

    if missing:
        print("=" * 50)
        print("  누락된 패키지가 있습니다!")
        print(f"  pip install {' '.join(missing)}")
        print("=" * 50)
        sys.exit(1)


def check_tesseract():
    """Tesseract OCR 설치 확인"""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def create_directories():
    """필요한 디렉토리 생성"""
    for d in ["config", "data/templates", "logs/screenshots"]:
        (PROJECT_ROOT / d).mkdir(parents=True, exist_ok=True)


def main():
    """메인 실행"""
    parser = argparse.ArgumentParser(description="TalkPC Auto Messenger")
    parser.add_argument("--saas", action="store_true", help="SaaS 모드 (서버 연결)")
    parser.add_argument("--server", default="http://localhost:8000", help="서버 URL")
    args = parser.parse_args()

    print("\n" + "=" * 50)
    mode_str = "SaaS" if args.saas else "로컬"
    print(f"  TalkPC Auto Messenger v1.1.0 ({mode_str} 모드)")
    print("=" * 50 + "\n")

    # 의존성 확인
    print("[1/3] 의존성 확인...")
    check_dependencies()
    print("  OK")

    # Tesseract 확인
    print("[2/3] Tesseract OCR 확인...")
    if check_tesseract():
        print("  OK")
    else:
        print("  Tesseract 없이 실행 (OCR 제한)")

    # 디렉토리 생성
    print("[3/3] 디렉토리 확인...")
    create_directories()
    print("  OK")

    # 오케스트레이터 초기화
    from core.orchestrator import Orchestrator
    from ui.app import App

    orchestrator = Orchestrator(base_dir=str(PROJECT_ROOT))

    # API 클라이언트 (SaaS 모드)
    api_client = None
    if args.saas:
        from core.api_client import APIClient
        api_client = APIClient(server_url=args.server)
        print(f"\n  서버: {args.server}")

    # UI 실행
    print("  앱 실행 중...\n")
    app = App(orchestrator=orchestrator, api_client=api_client)
    app.mainloop()


if __name__ == "__main__":
    main()

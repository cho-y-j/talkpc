"""
KakaoTalk Auto Messenger
========================
카카오톡 자동 메시지 발송 프로그램

사용법:
1. 카카오톡 PC 앱을 먼저 실행하세요
2. 이 프로그램을 실행하세요
3. 연락처를 등록하고 (엑셀 업로드 가능)
4. 메시지 템플릿을 작성하세요
5. 발송 시작!

요구사항:
- Python 3.10+
- Tesseract OCR 설치 필요
  - Mac: brew install tesseract tesseract-lang
  - Windows: https://github.com/tesseract-ocr/tesseract 에서 설치
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)


def check_dependencies():
    """의존성 확인"""
    missing = []

    try:
        import customtkinter
    except ImportError:
        missing.append("customtkinter")

    try:
        import pyautogui
    except ImportError:
        missing.append("pyautogui")

    try:
        import pytesseract
    except ImportError:
        missing.append("pytesseract")

    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")

    try:
        import openpyxl
    except ImportError:
        missing.append("openpyxl")

    if missing:
        print("=" * 50)
        print("  누락된 패키지가 있습니다!")
        print("=" * 50)
        print(f"\n  다음 명령어로 설치하세요:\n")
        print(f"  pip install {' '.join(missing)}")
        print(f"\n  또는:")
        print(f"  pip install -r requirements.txt")
        print("=" * 50)
        sys.exit(1)


def check_tesseract():
    """Tesseract OCR 설치 확인"""
    import platform
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        print("=" * 50)
        print("  Tesseract OCR가 설치되지 않았습니다!")
        print("=" * 50)
        if platform.system() == "Darwin":
            print("\n  Mac 설치 방법:")
            print("  brew install tesseract")
            print("  brew install tesseract-lang  # 한글 지원")
        elif platform.system() == "Windows":
            print("\n  Windows 설치 방법:")
            print("  https://github.com/UB-Mannheim/tesseract/wiki")
            print("  에서 설치파일 다운로드 후 설치")
            print("  설치 시 'Korean' 언어팩 체크")
        print("=" * 50)
        return False


def create_directories():
    """필요한 디렉토리 생성"""
    dirs = [
        PROJECT_ROOT / "config",
        PROJECT_ROOT / "data" / "templates",
        PROJECT_ROOT / "logs" / "screenshots",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def main():
    """메인 실행"""
    print("\n" + "=" * 50)
    print("  KakaoTalk Auto Messenger v1.0.0")
    print("=" * 50 + "\n")

    # 1. 의존성 확인
    print("[1/4] 의존성 확인...")
    check_dependencies()
    print("  ✅ 모든 패키지 설치 확인")

    # 2. Tesseract 확인
    print("[2/4] Tesseract OCR 확인...")
    tesseract_ok = check_tesseract()
    if tesseract_ok:
        print("  ✅ Tesseract OCR 설치 확인")
    else:
        print("  ⚠️  Tesseract 없이 실행합니다 (OCR 기능 제한)")

    # 3. 디렉토리 생성
    print("[3/4] 디렉토리 확인...")
    create_directories()
    print("  ✅ 디렉토리 준비 완료")

    # 4. 오케스트레이터 초기화
    print("[4/4] 앱 시작...")
    from core.orchestrator import Orchestrator
    from ui.app import App

    orchestrator = Orchestrator(base_dir=str(PROJECT_ROOT))

    # 5. UI 실행
    print("  ✅ 앱 실행 중...\n")
    app = App(orchestrator=orchestrator)
    app.mainloop()


if __name__ == "__main__":
    main()

"""
App - 메인 애플리케이션 윈도우
모든 페이지를 통합하는 최상위 UI
"""

import customtkinter as ctk
from ui.theme import AppTheme as T
from ui.components.sidebar import Sidebar
from ui.pages.dashboard_page import DashboardPage
from ui.pages.contact_page import ContactPage
from ui.pages.message_page import MessagePage
from ui.pages.send_page import SendPage
from ui.pages.settings_page import SettingsPage


class App(ctk.CTk):
    """메인 애플리케이션"""

    def __init__(self, orchestrator=None):
        super().__init__()
        self.orchestrator = orchestrator

        # -- 윈도우 설정 --
        self.title("KakaoTalk Auto Messenger")
        self.geometry("1100x750")
        self.minsize(900, 600)
        self.configure(fg_color=T.BG_DARK)

        # 다크 모드 설정
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # -- 레이아웃 --
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 사이드바
        self.sidebar = Sidebar(self, on_navigate=self._navigate)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        # 메인 콘텐츠 영역
        self.content_frame = ctk.CTkFrame(self, fg_color=T.BG_DARK, corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # -- 페이지 생성 --
        self.pages = {}
        self._create_pages()

        # -- 오케스트레이터 콜백 --
        if self.orchestrator:
            self.orchestrator.on_state_change(self._on_orch_state)
            self.orchestrator.on_log(self._on_orch_log)

        # 기본 페이지
        self._navigate("dashboard")

        # 저장된 설정이 있으면 자동 초기화 (앱 시작 후 0.5초 뒤)
        self.after(500, self._auto_init)

        # 예약 발송 스케줄러 시작
        if self.orchestrator:
            self.orchestrator.scheduler.start()

        # 닫기 처리
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_pages(self):
        """모든 페이지 생성"""
        self.pages["dashboard"] = DashboardPage(
            self.content_frame, orchestrator=self.orchestrator
        )
        self.pages["contacts"] = ContactPage(
            self.content_frame, orchestrator=self.orchestrator
        )
        self.pages["message"] = MessagePage(
            self.content_frame, orchestrator=self.orchestrator
        )
        self.pages["send"] = SendPage(
            self.content_frame, orchestrator=self.orchestrator,
            message_page=self.pages["message"]
        )
        self.pages["settings"] = SettingsPage(
            self.content_frame, orchestrator=self.orchestrator
        )

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def _navigate(self, page_id: str):
        """페이지 네비게이션"""
        if page_id in self.pages:
            self.pages[page_id].tkraise()
            self.sidebar.set_active(page_id)

            # 페이지 진입시 새로고침
            if page_id == "dashboard":
                self.pages["dashboard"].refresh_stats()
            elif page_id == "contacts":
                self.pages["contacts"].refresh_list()

    def _on_orch_state(self, state):
        """오케스트레이터 상태 변경 (스레드 → 메인 스레드)"""
        def _update():
            state_map = {
                "idle": ("● 대기 중", T.TEXT_MUTED),
                "initializing": ("◌ 초기화 중...", T.WARNING),
                "ready": ("● 준비 완료", T.SUCCESS),
                "sending": ("◉ 발송 중...", T.ACCENT),
                "paused": ("◎ 일시정지", T.WARNING),
                "completed": ("✓ 발송 완료", T.SUCCESS),
                "error": ("✗ 오류", T.ERROR)
            }
            text, color = state_map.get(state, ("● 알 수 없음", T.TEXT_MUTED))
            self.sidebar.update_status(text, color)
        self.after(0, _update)

    def _on_orch_log(self, message, level):
        """오케스트레이터 로그 → 대시보드 (스레드 → 메인 스레드)"""
        def _update():
            if "dashboard" in self.pages:
                self.pages["dashboard"].add_log(message, level)
        self.after(0, _update)

    def _auto_init(self):
        """앱 시작 시 저장된 설정 자동 로드 + 카카오톡 자동 배치"""
        if "dashboard" in self.pages:
            self.pages["dashboard"].auto_initialize()

    def _on_close(self):
        """앱 종료"""
        if self.orchestrator:
            if self.orchestrator.state == "sending":
                self.orchestrator.stop_sending()
            self.orchestrator.scheduler.stop()
        self.destroy()

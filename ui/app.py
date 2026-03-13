"""
App - 메인 애플리케이션 윈도우
SaaS 모드: 로그인 → 메인앱 전환
로컬 모드: 직접 메인앱 (기존 동작)
"""

import customtkinter as ctk
from ui.theme import AppTheme as T
from ui.components.sidebar import Sidebar
from ui.pages.dashboard_page import DashboardPage
from ui.pages.contact_page import ContactPage
from ui.pages.message_page import MessagePage
from ui.pages.send_page import SendPage
from ui.pages.settings_page import SettingsPage
from ui.pages.login_page import LoginPage
from ui.pages.usage_page import UsagePage


class App(ctk.CTk):
    """메인 애플리케이션"""

    def __init__(self, orchestrator=None, api_client=None):
        super().__init__()
        self.orchestrator = orchestrator
        self.api_client = api_client
        self.saas_mode = api_client is not None

        # -- 윈도우 설정 --
        self.title("TalkPC - Auto Messenger")
        self.geometry("1100x750")
        self.minsize(900, 600)
        self.configure(fg_color=T.BG_DARK)

        # 다크 모드 설정
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # -- 레이아웃 --
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        if self.saas_mode:
            # SaaS 모드: 먼저 로그인 화면 표시
            self._show_login()
        else:
            # 로컬 모드: 바로 메인 화면
            self._show_main()

        # 닫기 처리
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _show_login(self):
        """로그인 화면 표시"""
        # 기존 위젯 제거
        for w in self.winfo_children():
            w.destroy()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        self.login_page = LoginPage(
            self, api_client=self.api_client,
            on_login_success=self._on_login_success
        )
        self.login_page.grid(row=0, column=0, sticky="nsew")

    def _on_login_success(self):
        """로그인 성공 → 메인 화면 전환"""
        self._show_main()

    def _show_main(self):
        """메인 화면 구성"""
        # 기존 위젯 제거
        for w in self.winfo_children():
            w.destroy()

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 사이드바
        self.sidebar = Sidebar(self, on_navigate=self._navigate,
                               api_client=self.api_client,
                               on_logout=self._on_logout if self.saas_mode else None)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        # 메인 콘텐츠 영역
        self.content_frame = ctk.CTkFrame(self, fg_color=T.BG_DARK, corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # 페이지 생성
        self.pages = {}
        self._create_pages()

        # 오케스트레이터 콜백
        if self.orchestrator:
            self.orchestrator.on_state_change(self._on_orch_state)
            self.orchestrator.on_log(self._on_orch_log)

        # 기본 페이지
        self._navigate("dashboard")

        # 자동 초기화 (0.5초 후)
        self.after(500, self._auto_init)

        # 예약 발송 스케줄러 시작
        if self.orchestrator:
            self.orchestrator.scheduler.start()

        # SaaS 모드 잔액 갱신
        if self.saas_mode:
            self.after(1000, self._refresh_balance)

    def _create_pages(self):
        """모든 페이지 생성"""
        self.pages["dashboard"] = DashboardPage(
            self.content_frame, orchestrator=self.orchestrator,
            api_client=self.api_client
        )
        self.pages["contacts"] = ContactPage(
            self.content_frame, orchestrator=self.orchestrator,
            api_client=self.api_client
        )
        self.pages["message"] = MessagePage(
            self.content_frame, orchestrator=self.orchestrator
        )
        self.pages["send"] = SendPage(
            self.content_frame, orchestrator=self.orchestrator,
            message_page=self.pages["message"],
            api_client=self.api_client
        )
        self.pages["settings"] = SettingsPage(
            self.content_frame, orchestrator=self.orchestrator
        )

        if self.saas_mode:
            self.pages["usage"] = UsagePage(
                self.content_frame, api_client=self.api_client
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
            elif page_id == "usage" and self.saas_mode:
                self.pages["usage"].refresh()

    def _on_orch_state(self, state):
        """오케스트레이터 상태 변경"""
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
        """오케스트레이터 로그 → 대시보드"""
        def _update():
            if "dashboard" in self.pages:
                self.pages["dashboard"].add_log(message, level)
        self.after(0, _update)

    def _auto_init(self):
        """앱 시작 시 저장된 설정 자동 로드"""
        if "dashboard" in self.pages:
            self.pages["dashboard"].auto_initialize()

    def _refresh_balance(self):
        """SaaS 모드: 잔액 갱신"""
        if self.api_client and self.api_client.is_logged_in:
            try:
                balance = self.api_client.get_balance()
                self.sidebar.update_balance(balance)
            except Exception:
                pass

    def _on_logout(self):
        """로그아웃 → 로그인 화면"""
        if self.orchestrator:
            if self.orchestrator.state == "sending":
                self.orchestrator.stop_sending()
            self.orchestrator.scheduler.stop()
        if self.api_client:
            self.api_client.logout()
        self._show_login()

    def _on_close(self):
        """앱 종료"""
        if self.orchestrator:
            if self.orchestrator.state == "sending":
                self.orchestrator.stop_sending()
            self.orchestrator.scheduler.stop()
        self.destroy()

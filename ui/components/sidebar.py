"""
Sidebar - 좌측 네비게이션 사이드바
SaaS 모드: 잔액 표시, 사용량 메뉴, 로그아웃
"""

import customtkinter as ctk
from ui.theme import AppTheme as T


class Sidebar(ctk.CTkFrame):
    """좌측 사이드바 네비게이션"""

    def __init__(self, parent, on_navigate=None, api_client=None,
                 on_logout=None, **kwargs):
        super().__init__(parent, width=T.SIDEBAR_WIDTH, corner_radius=0, **kwargs)
        self.configure(fg_color=T.BG_SIDEBAR)
        self.on_navigate = on_navigate
        self.api_client = api_client
        self.on_logout = on_logout
        self.buttons = {}
        self.active_page = None

        self.grid_propagate(False)
        self._build()

    def _build(self):
        # -- 로고 영역 --
        logo_frame = ctk.CTkFrame(self, fg_color="transparent", height=80)
        logo_frame.pack(fill="x", padx=16, pady=(20, 10))
        logo_frame.pack_propagate(False)

        logo_label = ctk.CTkLabel(
            logo_frame, text="💬",
            font=(T.get_font_family(), 28), text_color=T.ACCENT
        )
        logo_label.pack(pady=(5, 0))

        ctk.CTkLabel(
            logo_frame, text="TalkPC",
            font=(T.get_font_family(), 13, "bold"), text_color=T.TEXT_PRIMARY
        ).pack()

        ctk.CTkLabel(
            logo_frame, text="Auto Messenger",
            font=(T.get_font_family(), 10), text_color=T.TEXT_SECONDARY
        ).pack()

        # -- 사용자 정보 (SaaS 모드) --
        if self.api_client:
            user_frame = ctk.CTkFrame(self, fg_color=T.BG_HOVER, corner_radius=8)
            user_frame.pack(fill="x", padx=12, pady=(0, 5))

            name = self.api_client.user_info.get("name", "")
            ctk.CTkLabel(
                user_frame, text=f"👤 {name}",
                font=(T.get_font_family(), 11), text_color=T.TEXT_PRIMARY
            ).pack(anchor="w", padx=10, pady=(8, 2))

            self.balance_label = ctk.CTkLabel(
                user_frame, text="잔액: -원",
                font=(T.get_font_family(), 10, "bold"), text_color=T.SUCCESS
            )
            self.balance_label.pack(anchor="w", padx=10, pady=(0, 8))

        # -- 구분선 --
        ctk.CTkFrame(self, fg_color=T.BORDER, height=1).pack(fill="x", padx=16, pady=10)

        # -- 메뉴 버튼 --
        menu_items = [
            ("dashboard", "📊  대시보드"),
            ("contacts", "👥  연락처"),
            ("message", "💬  메시지"),
            ("send", "🚀  발송"),
        ]

        # 템플릿 디자이너
        menu_items.append(("alimtalk_designer", "💛  알림톡 디자이너"))
        menu_items.append(("rcs_designer", "📱  RCS 디자이너"))

        # SaaS 모드: 사용량/충전 메뉴 추가
        if self.api_client:
            menu_items.append(("usage", "📈  사용량"))
            menu_items.append(("charge", "💳  충전하기"))

        menu_items.append(("settings", "⚙️  설정"))

        for page_id, label in menu_items:
            btn = ctk.CTkButton(
                self, text=label, font=(T.get_font_family(), 13),
                anchor="w", height=42, corner_radius=8,
                fg_color="transparent", text_color=T.TEXT_SECONDARY,
                hover_color=T.BG_HOVER,
                command=lambda pid=page_id: self._on_click(pid)
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.buttons[page_id] = btn

        # -- 하단 --
        spacer = ctk.CTkFrame(self, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        ctk.CTkFrame(self, fg_color=T.BORDER, height=1).pack(fill="x", padx=16, pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            self, text="● 대기 중",
            font=(T.get_font_family(), 10), text_color=T.TEXT_MUTED
        )
        self.status_label.pack(padx=16, pady=(0, 5))

        # 로그아웃 버튼 (SaaS 모드)
        if self.on_logout:
            ctk.CTkButton(
                self, text="로그아웃", height=30, width=100,
                font=(T.get_font_family(), 10),
                fg_color="transparent", text_color=T.ERROR,
                hover_color=T.BG_HOVER,
                command=self.on_logout
            ).pack(pady=(0, 5))

        ctk.CTkLabel(
            self, text="v1.1.0",
            font=(T.get_font_family(), 9), text_color=T.TEXT_MUTED
        ).pack(padx=16, pady=(0, 16))

        # 기본 선택
        self.set_active("dashboard")

    def _on_click(self, page_id: str):
        self.set_active(page_id)
        if self.on_navigate:
            self.on_navigate(page_id)

    def set_active(self, page_id: str):
        """활성 메뉴 설정"""
        self.active_page = page_id
        for pid, btn in self.buttons.items():
            if pid == page_id:
                btn.configure(fg_color=T.ACCENT, text_color=T.TEXT_ON_ACCENT,
                              hover_color=T.ACCENT_HOVER)
            else:
                btn.configure(fg_color="transparent", text_color=T.TEXT_SECONDARY,
                              hover_color=T.BG_HOVER)

    def update_status(self, text: str, color: str = None):
        """하단 상태 텍스트 업데이트"""
        self.status_label.configure(text=text, text_color=color or T.TEXT_MUTED)

    def update_balance(self, balance: int):
        """잔액 업데이트 (SaaS 모드)"""
        if hasattr(self, "balance_label"):
            self.balance_label.configure(text=f"잔액: {balance:,}원")

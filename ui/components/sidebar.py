"""
Sidebar - 좌측 네비게이션 사이드바
"""

import customtkinter as ctk
from ui.theme import AppTheme as T


class Sidebar(ctk.CTkFrame):
    """좌측 사이드바 네비게이션"""

    def __init__(self, parent, on_navigate=None, **kwargs):
        super().__init__(parent, width=T.SIDEBAR_WIDTH, corner_radius=0, **kwargs)
        self.configure(fg_color=T.BG_SIDEBAR)
        self.on_navigate = on_navigate
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
            logo_frame,
            text="💬",
            font=(T.get_font_family(), 28),
            text_color=T.ACCENT
        )
        logo_label.pack(pady=(5, 0))

        app_name = ctk.CTkLabel(
            logo_frame,
            text="KakaoTalk",
            font=(T.get_font_family(), 13, "bold"),
            text_color=T.TEXT_PRIMARY
        )
        app_name.pack()

        app_sub = ctk.CTkLabel(
            logo_frame,
            text="Auto Messenger",
            font=(T.get_font_family(), 10),
            text_color=T.TEXT_SECONDARY
        )
        app_sub.pack()

        # -- 구분선 --
        separator = ctk.CTkFrame(self, fg_color=T.BORDER, height=1)
        separator.pack(fill="x", padx=16, pady=10)

        # -- 메뉴 버튼 --
        menu_items = [
            ("dashboard", "📊  대시보드"),
            ("contacts", "👥  연락처"),
            ("message", "💬  메시지"),
            ("send", "🚀  발송"),
            ("settings", "⚙️  설정"),
        ]

        for page_id, label in menu_items:
            btn = ctk.CTkButton(
                self,
                text=label,
                font=(T.get_font_family(), 13),
                anchor="w",
                height=42,
                corner_radius=8,
                fg_color="transparent",
                text_color=T.TEXT_SECONDARY,
                hover_color=T.BG_HOVER,
                command=lambda pid=page_id: self._on_click(pid)
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.buttons[page_id] = btn

        # -- 하단 상태 --
        spacer = ctk.CTkFrame(self, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        separator2 = ctk.CTkFrame(self, fg_color=T.BORDER, height=1)
        separator2.pack(fill="x", padx=16, pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            self,
            text="● 대기 중",
            font=(T.get_font_family(), 10),
            text_color=T.TEXT_MUTED
        )
        self.status_label.pack(padx=16, pady=(0, 5))

        version_label = ctk.CTkLabel(
            self,
            text="v1.0.0",
            font=(T.get_font_family(), 9),
            text_color=T.TEXT_MUTED
        )
        version_label.pack(padx=16, pady=(0, 16))

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
                btn.configure(
                    fg_color=T.ACCENT,
                    text_color=T.TEXT_ON_ACCENT,
                    hover_color=T.ACCENT_HOVER
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=T.TEXT_SECONDARY,
                    hover_color=T.BG_HOVER
                )

    def update_status(self, text: str, color: str = None):
        """하단 상태 텍스트 업데이트"""
        self.status_label.configure(text=text, text_color=color or T.TEXT_MUTED)

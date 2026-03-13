"""로그인/회원가입 페이지"""
import customtkinter as ctk
from ui.theme import AppTheme as T
from typing import Callable, Optional


class LoginPage(ctk.CTkFrame):
    """로그인 + 회원가입 통합 페이지"""

    def __init__(self, parent, api_client=None, on_login_success: Optional[Callable] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color=T.BG_DARK)
        self.api_client = api_client
        self.on_login_success = on_login_success
        self.is_register_mode = False
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 중앙 카드
        card = ctk.CTkFrame(self, fg_color=T.BG_CARD, corner_radius=16, width=400)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # 로고
        ctk.CTkLabel(card, text="💬", font=(T.get_font_family(), 36)).pack(pady=(30, 5))
        ctk.CTkLabel(card, text="TalkPC", font=(T.get_font_family(), 20, "bold"),
                     text_color=T.TEXT_PRIMARY).pack()
        ctk.CTkLabel(card, text="Auto Messenger", font=(T.get_font_family(), 11),
                     text_color=T.TEXT_MUTED).pack(pady=(0, 20))

        # 에러 메시지
        self.error_label = ctk.CTkLabel(card, text="", text_color=T.ERROR,
                                        font=(T.get_font_family(), 11))
        self.error_label.pack(padx=30)

        # 입력 필드 프레임
        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=30, pady=10)

        # 이름 (회원가입시만)
        self.name_frame = ctk.CTkFrame(form, fg_color="transparent")
        ctk.CTkLabel(self.name_frame, text="이름", font=(T.get_font_family(), 12),
                     text_color=T.TEXT_SECONDARY).pack(anchor="w")
        self.name_entry = ctk.CTkEntry(self.name_frame, height=38,
                                       placeholder_text="이름 입력")
        self.name_entry.pack(fill="x", pady=(2, 8))

        # 아이디
        ctk.CTkLabel(form, text="아이디", font=(T.get_font_family(), 12),
                     text_color=T.TEXT_SECONDARY).pack(anchor="w")
        self.username_entry = ctk.CTkEntry(form, height=38,
                                           placeholder_text="아이디 입력")
        self.username_entry.pack(fill="x", pady=(2, 8))

        # 비밀번호
        ctk.CTkLabel(form, text="비밀번호", font=(T.get_font_family(), 12),
                     text_color=T.TEXT_SECONDARY).pack(anchor="w")
        self.password_entry = ctk.CTkEntry(form, height=38, show="*",
                                           placeholder_text="비밀번호 입력")
        self.password_entry.pack(fill="x", pady=(2, 8))

        # 전화번호 (회원가입시만)
        self.phone_frame = ctk.CTkFrame(form, fg_color="transparent")
        ctk.CTkLabel(self.phone_frame, text="전화번호", font=(T.get_font_family(), 12),
                     text_color=T.TEXT_SECONDARY).pack(anchor="w")
        self.phone_entry = ctk.CTkEntry(self.phone_frame, height=38,
                                        placeholder_text="01012345678")
        self.phone_entry.pack(fill="x", pady=(2, 8))

        # 로그인/가입 버튼
        self.action_btn = ctk.CTkButton(form, text="로그인", height=42,
                                        font=(T.get_font_family(), 14, "bold"),
                                        fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                                        command=self._do_action)
        self.action_btn.pack(fill="x", pady=(10, 5))

        # 모드 전환
        self.toggle_btn = ctk.CTkButton(form, text="계정이 없으신가요? 회원가입",
                                        font=(T.get_font_family(), 11),
                                        fg_color="transparent", hover_color=T.BG_HOVER,
                                        text_color=T.ACCENT,
                                        command=self._toggle_mode)
        self.toggle_btn.pack(fill="x", pady=(0, 5))

        # 서버 URL
        server_frame = ctk.CTkFrame(form, fg_color="transparent")
        server_frame.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(server_frame, text="서버", font=(T.get_font_family(), 10),
                     text_color=T.TEXT_MUTED).pack(side="left")
        self.server_entry = ctk.CTkEntry(server_frame, height=28,
                                         font=(T.get_font_family(), 10),
                                         placeholder_text="http://localhost:8000")
        self.server_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.server_entry.insert(0, "http://localhost:8000")

        # 하단 여백
        ctk.CTkLabel(card, text="", height=10).pack()

        # Enter 키 바인딩
        self.password_entry.bind("<Return>", lambda e: self._do_action())

    def _toggle_mode(self):
        self.is_register_mode = not self.is_register_mode
        self.error_label.configure(text="")
        if self.is_register_mode:
            self.name_frame.pack(in_=self.username_entry.master,
                                 before=self.username_entry.master.winfo_children()[0],
                                 fill="x")
            self.phone_frame.pack(in_=self.password_entry.master,
                                  after=self.password_entry, fill="x")
            self.action_btn.configure(text="회원가입")
            self.toggle_btn.configure(text="이미 계정이 있으신가요? 로그인")
        else:
            self.name_frame.pack_forget()
            self.phone_frame.pack_forget()
            self.action_btn.configure(text="로그인")
            self.toggle_btn.configure(text="계정이 없으신가요? 회원가입")

    def _do_action(self):
        self.error_label.configure(text="")
        server_url = self.server_entry.get().strip()
        if server_url:
            self.api_client.server_url = server_url.rstrip("/")

        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            self.error_label.configure(text="아이디와 비밀번호를 입력하세요")
            return

        try:
            if self.is_register_mode:
                name = self.name_entry.get().strip()
                phone = self.phone_entry.get().strip()
                if not name:
                    self.error_label.configure(text="이름을 입력하세요")
                    return
                self.api_client.register(username, password, name, phone)
            else:
                self.api_client.login(username, password)

            if self.on_login_success:
                self.on_login_success()

        except Exception as e:
            detail = str(e)
            try:
                import json
                detail = json.loads(e.response.text).get("detail", detail)
            except Exception:
                pass
            self.error_label.configure(text=detail)

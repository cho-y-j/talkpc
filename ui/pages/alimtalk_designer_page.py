"""알림톡 템플릿 디자이너 - 카카오 검수용 템플릿 설계 + 미리보기 + 가이드"""
import customtkinter as ctk
from tkinter import messagebox, filedialog
from ui.theme import AppTheme as T


class AlimtalkDesignerPage(ctk.CTkFrame):
    """알림톡 템플릿 설계 + 카카오 제출 가이드"""

    TEMPLATE_TYPES = {
        "basic": "기본형",
        "emphasize": "강조 표기형",
        "image": "이미지형",
        "item_list": "아이템리스트형",
    }

    BUTTON_TYPES = {
        "WL": "웹 링크",
        "AL": "앱 링크",
        "BK": "봇 키워드",
        "MD": "메시지 전달",
        "DS": "배송 조회",
        "AC": "채널 추가",
    }

    CATEGORIES = [
        "회원가입", "주문/배송", "예약/신청", "결제", "알림/공지",
        "인증", "고객상담", "이벤트당첨", "기타",
    ]

    def __init__(self, parent, api_client=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color=T.BG_DARK)
        self.api_client = api_client
        self.buttons_data = []
        self.image_path = None
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 헤더
        header = ctk.CTkFrame(self, fg_color="transparent", height=40)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 8))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="알림톡 템플릿 디자이너",
                     font=(T.get_font_family(), 16, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(side="left")

        # 탭 버튼
        tab_frame = ctk.CTkFrame(header, fg_color="transparent")
        tab_frame.pack(side="right")
        self.tab_buttons = {}
        for tab_id, label in [("designer", "디자이너"), ("guide", "제작 가이드")]:
            btn = ctk.CTkButton(tab_frame, text=label, width=90, height=30,
                                font=(T.get_font_family(), 11),
                                fg_color=T.BG_HOVER, hover_color=T.BORDER,
                                text_color=T.TEXT_PRIMARY, corner_radius=6,
                                command=lambda t=tab_id: self._switch_tab(t))
            btn.pack(side="left", padx=2)
            self.tab_buttons[tab_id] = btn

        # 메인 콘텐츠 (탭)
        self.tab_container = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_container.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 16))
        self.tab_container.grid_columnconfigure(0, weight=1)
        self.tab_container.grid_rowconfigure(0, weight=1)

        self.tabs = {}
        self._build_designer_tab()
        self._build_guide_tab()
        self._switch_tab("designer")

    # ══════════════════════════════════════
    #  디자이너 탭
    # ══════════════════════════════════════

    def _build_designer_tab(self):
        tab = ctk.CTkFrame(self.tab_container, fg_color="transparent")
        tab.grid(row=0, column=0, sticky="nsew")
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(0, weight=1)
        self.tabs["designer"] = tab

        # ── 좌측: 에디터 ──
        left = ctk.CTkScrollableFrame(tab, fg_color=T.BG_CARD, corner_radius=10,
                                       scrollbar_button_color=T.BG_HOVER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # 템플릿 유형
        ctk.CTkLabel(left, text="템플릿 유형", font=(T.get_font_family(), 12, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(12, 4))
        self.type_var = ctk.StringVar(value="basic")
        type_frame = ctk.CTkFrame(left, fg_color="transparent")
        type_frame.pack(fill="x", padx=16, pady=(0, 8))
        for val, label in self.TEMPLATE_TYPES.items():
            ctk.CTkRadioButton(type_frame, text=label, variable=self.type_var, value=val,
                               font=(T.get_font_family(), 11), text_color=T.TEXT_PRIMARY,
                               fg_color="#58a6ff", border_color=T.BORDER,
                               command=self._on_type_change
                               ).pack(side="left", padx=(0, 12))

        # 카테고리
        ctk.CTkLabel(left, text="카테고리", font=(T.get_font_family(), 12, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(8, 4))
        self.category_var = ctk.StringVar(value="알림/공지")
        ctk.CTkComboBox(left, values=self.CATEGORIES, variable=self.category_var,
                        font=(T.get_font_family(), 11), width=200, height=30,
                        fg_color=T.BG_INPUT, border_color=T.BORDER,
                        text_color=T.TEXT_PRIMARY, dropdown_fg_color=T.BG_CARD
                        ).pack(anchor="w", padx=16, pady=(0, 8))

        # 템플릿 코드명
        ctk.CTkLabel(left, text="템플릿 코드 (영문, 카카오 등록용)",
                     font=(T.get_font_family(), 12, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(8, 4))
        self.code_entry = ctk.CTkEntry(left, placeholder_text="예: order_complete_001",
                                        font=(T.get_font_family(), 11),
                                        fg_color=T.BG_INPUT, border_color=T.BORDER,
                                        text_color=T.TEXT_PRIMARY, height=32)
        self.code_entry.pack(fill="x", padx=16, pady=(0, 8))

        # 강조 제목 (강조형일 때)
        self.emphasize_frame = ctk.CTkFrame(left, fg_color="transparent")
        ctk.CTkLabel(self.emphasize_frame, text="강조 제목 (최대 50자)",
                     font=(T.get_font_family(), 12, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w")
        self.emphasize_entry = ctk.CTkEntry(self.emphasize_frame,
                                             placeholder_text="예: 주문이 완료되었습니다",
                                             font=(T.get_font_family(), 11),
                                             fg_color=T.BG_INPUT, border_color=T.BORDER,
                                             text_color=T.TEXT_PRIMARY, height=32)
        self.emphasize_entry.pack(fill="x", pady=(4, 0))

        # 이미지 (이미지형일 때)
        self.image_frame = ctk.CTkFrame(left, fg_color="transparent")
        ctk.CTkLabel(self.image_frame, text="헤더 이미지 (800x400px, jpg/png, 500KB 이하)",
                     font=(T.get_font_family(), 12, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w")
        img_btn_frame = ctk.CTkFrame(self.image_frame, fg_color="transparent")
        img_btn_frame.pack(fill="x", pady=(4, 0))
        ctk.CTkButton(img_btn_frame, text="이미지 선택", width=100, height=28,
                      font=(T.get_font_family(), 10), fg_color=T.BG_HOVER,
                      hover_color=T.BORDER, text_color=T.TEXT_PRIMARY,
                      command=self._select_image).pack(side="left")
        self.img_label = ctk.CTkLabel(img_btn_frame, text="선택 안됨",
                                       font=(T.get_font_family(), 10),
                                       text_color=T.TEXT_MUTED)
        self.img_label.pack(side="left", padx=8)

        # 본문 메시지
        ctk.CTkLabel(left, text="본문 메시지", font=(T.get_font_family(), 12, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(8, 4))

        # 변수 삽입 버튼
        var_frame = ctk.CTkFrame(left, fg_color="transparent")
        var_frame.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(var_frame, text="변수:", font=(T.get_font_family(), 10),
                     text_color=T.TEXT_MUTED).pack(side="left")
        for var in ["#{이름}", "#{주문번호}", "#{금액}", "#{날짜}", "#{상품명}", "#{URL}"]:
            ctk.CTkButton(var_frame, text=var, width=70, height=22,
                          font=(T.get_font_family(), 9), fg_color=T.BG_HOVER,
                          hover_color=T.BORDER, text_color="#58a6ff", corner_radius=4,
                          command=lambda v=var: self.body_editor.insert("insert", v)
                          ).pack(side="left", padx=2)

        self.body_editor = ctk.CTkTextbox(left, height=200,
                                           font=(T.get_font_family(), 12),
                                           fg_color=T.BG_INPUT, text_color=T.TEXT_PRIMARY,
                                           corner_radius=6, border_width=1,
                                           border_color=T.BORDER)
        self.body_editor.pack(fill="x", padx=16, pady=(0, 4))
        self.body_editor.insert("1.0",
            "안녕하세요 #{이름}님,\n\n"
            "주문하신 상품의 배송이 시작되었습니다.\n\n"
            "■ 주문번호: #{주문번호}\n"
            "■ 상품명: #{상품명}\n"
            "■ 배송시작일: #{날짜}\n\n"
            "감사합니다.")
        self.body_editor.bind("<KeyRelease>", lambda e: self._update_preview())

        # 글자 수 표시
        self.char_count = ctk.CTkLabel(left, text="0 / 1000자",
                                        font=(T.get_font_family(), 9),
                                        text_color=T.TEXT_MUTED)
        self.char_count.pack(anchor="e", padx=16)

        # ── 버튼 설정 ──
        ctk.CTkLabel(left, text="버튼 (최대 5개)", font=(T.get_font_family(), 12, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(8, 4))

        self.buttons_frame = ctk.CTkFrame(left, fg_color="transparent")
        self.buttons_frame.pack(fill="x", padx=16, pady=(0, 4))

        add_btn_frame = ctk.CTkFrame(left, fg_color="transparent")
        add_btn_frame.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkButton(add_btn_frame, text="+ 버튼 추가", width=100, height=28,
                      font=(T.get_font_family(), 10), fg_color="#1a3a5c",
                      hover_color="#2471a3", text_color="#58a6ff",
                      command=self._add_button).pack(side="left")

        # 초기 버튼 1개
        self._add_button()

        # ── 우측: 미리보기 ──
        right = ctk.CTkFrame(tab, fg_color=T.BG_CARD, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="카카오톡 미리보기",
                     font=(T.get_font_family(), 13, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(padx=16, pady=(12, 8), anchor="w")

        # 폰 프레임
        phone = ctk.CTkFrame(right, fg_color="#b2c7d9", corner_radius=20,
                              width=320, height=500)
        phone.pack(padx=20, pady=(0, 12))
        phone.pack_propagate(False)

        # 카톡 헤더
        kakao_header = ctk.CTkFrame(phone, fg_color="#90b4ce", height=40, corner_radius=0)
        kakao_header.pack(fill="x")
        kakao_header.pack_propagate(False)
        ctk.CTkLabel(kakao_header, text="카카오톡",
                     font=(T.get_font_family(), 12, "bold"),
                     text_color="#3a3a3a").pack(side="left", padx=12, pady=8)

        # 메시지 영역
        self.preview_area = ctk.CTkScrollableFrame(phone, fg_color="#b2c7d9",
                                                    scrollbar_button_color="#90b4ce")
        self.preview_area.pack(fill="both", expand=True, padx=8, pady=8)

        # 하단: 복사/내보내기
        bottom = ctk.CTkFrame(right, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkButton(bottom, text="템플릿 텍스트 복사", width=140, height=30,
                      font=(T.get_font_family(), 11), fg_color="#58a6ff",
                      hover_color="#4090e0", text_color="#ffffff",
                      command=self._copy_template).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bottom, text="미리보기 갱신", width=100, height=30,
                      font=(T.get_font_family(), 11), fg_color=T.BG_HOVER,
                      hover_color=T.BORDER, text_color=T.TEXT_PRIMARY,
                      command=self._update_preview).pack(side="left")

        # 단가 안내
        ctk.CTkLabel(right, text="알림톡 단가: 7원/건 (대체발송 SMS 8원, LMS 25원)",
                     font=(T.get_font_family(), 10), text_color=T.TEXT_MUTED
                     ).pack(padx=16, pady=(0, 8))

        self._update_preview()

    def _add_button(self):
        if len(self.buttons_data) >= 5:
            return
        idx = len(self.buttons_data)
        row = ctk.CTkFrame(self.buttons_frame, fg_color=T.BG_INPUT, corner_radius=6)
        row.pack(fill="x", pady=2)

        type_var = ctk.StringVar(value="WL")
        ctk.CTkComboBox(row, values=list(self.BUTTON_TYPES.keys()),
                        variable=type_var, width=70, height=26,
                        font=(T.get_font_family(), 9), fg_color=T.BG_DARK,
                        border_color=T.BORDER, text_color=T.TEXT_PRIMARY,
                        dropdown_fg_color=T.BG_CARD).pack(side="left", padx=4, pady=4)

        name_entry = ctk.CTkEntry(row, placeholder_text="버튼명",
                                   font=(T.get_font_family(), 10), width=100, height=26,
                                   fg_color=T.BG_DARK, border_color=T.BORDER,
                                   text_color=T.TEXT_PRIMARY)
        name_entry.pack(side="left", padx=2, pady=4)
        name_entry.insert(0, "자세히 보기" if idx == 0 else "")

        url_entry = ctk.CTkEntry(row, placeholder_text="URL / 키워드",
                                  font=(T.get_font_family(), 10), height=26,
                                  fg_color=T.BG_DARK, border_color=T.BORDER,
                                  text_color=T.TEXT_PRIMARY)
        url_entry.pack(side="left", fill="x", expand=True, padx=2, pady=4)
        url_entry.insert(0, "https://" if idx == 0 else "")

        ctk.CTkButton(row, text="✕", width=24, height=24,
                      font=(T.get_font_family(), 10), fg_color="transparent",
                      hover_color=T.ERROR, text_color=T.TEXT_MUTED,
                      command=lambda r=row, i=idx: self._remove_button(r, i)
                      ).pack(side="right", padx=4, pady=4)

        self.buttons_data.append({"row": row, "type": type_var,
                                   "name": name_entry, "url": url_entry})

    def _remove_button(self, row, idx):
        row.destroy()
        self.buttons_data = [b for b in self.buttons_data if b["row"].winfo_exists()]

    def _on_type_change(self):
        t = self.type_var.get()
        self.emphasize_frame.pack_forget()
        self.image_frame.pack_forget()
        if t == "emphasize":
            self.emphasize_frame.pack(fill="x", padx=16, pady=(0, 8))
        elif t == "image":
            self.image_frame.pack(fill="x", padx=16, pady=(0, 8))
        self._update_preview()

    def _select_image(self):
        fp = filedialog.askopenfilename(
            filetypes=[("이미지", "*.jpg *.jpeg *.png")])
        if fp:
            import os
            self.image_path = fp
            self.img_label.configure(text=os.path.basename(fp), text_color="#58a6ff")
            self._update_preview()

    def _update_preview(self):
        for w in self.preview_area.winfo_children():
            w.destroy()

        body = self.body_editor.get("1.0", "end").strip()
        t = self.type_var.get()

        # 글자 수
        self.char_count.configure(text=f"{len(body)} / 1000자",
                                   text_color=T.ERROR if len(body) > 1000 else T.TEXT_MUTED)

        # 카톡 말풍선
        bubble = ctk.CTkFrame(self.preview_area, fg_color="#ffffff",
                               corner_radius=12, border_width=0)
        bubble.pack(fill="x", pady=4, padx=4)

        # 발신 프로필
        prof = ctk.CTkFrame(bubble, fg_color="transparent")
        prof.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(prof, text="🏢", font=(T.get_font_family(), 16)).pack(side="left")
        ctk.CTkLabel(prof, text="TalkPC", font=(T.get_font_family(), 11, "bold"),
                     text_color="#333333").pack(side="left", padx=4)
        ctk.CTkLabel(prof, text="알림톡", font=(T.get_font_family(), 9),
                     text_color="#999999").pack(side="left")

        # 강조 표기
        if t == "emphasize":
            emph_text = self.emphasize_entry.get() or "강조 제목"
            ctk.CTkLabel(bubble, text=emph_text,
                         font=(T.get_font_family(), 15, "bold"),
                         text_color="#333333", wraplength=260
                         ).pack(fill="x", padx=12, pady=(8, 0))

        # 이미지
        if t == "image":
            img_placeholder = ctk.CTkFrame(bubble, fg_color="#e0e0e0",
                                            height=100, corner_radius=6)
            img_placeholder.pack(fill="x", padx=10, pady=(8, 0))
            img_placeholder.pack_propagate(False)
            ctk.CTkLabel(img_placeholder, text="🖼 800 x 400 이미지",
                         font=(T.get_font_family(), 11),
                         text_color="#888888").pack(expand=True)

        # 본문
        # 변수 미리보기 치환
        preview_body = body.replace("#{이름}", "홍길동").replace("#{주문번호}", "20260313-001")
        preview_body = preview_body.replace("#{금액}", "50,000원").replace("#{날짜}", "2026.03.15")
        preview_body = preview_body.replace("#{상품명}", "테스트 상품").replace("#{URL}", "https://example.com")

        ctk.CTkLabel(bubble, text=preview_body,
                     font=(T.get_font_family(), 11),
                     text_color="#333333", wraplength=260, justify="left"
                     ).pack(fill="x", padx=12, pady=8)

        # 버튼들
        for btn in self.buttons_data:
            if not btn["row"].winfo_exists():
                continue
            name = btn["name"].get() or "버튼"
            btn_widget = ctk.CTkButton(bubble, text=name, height=32,
                                        font=(T.get_font_family(), 11),
                                        fg_color="#f5f5f5", hover_color="#e8e8e8",
                                        text_color="#4a90d9", corner_radius=6,
                                        border_width=1, border_color="#d5d5d5")
            btn_widget.pack(fill="x", padx=10, pady=(0, 4))

        # 하단 여백
        ctk.CTkFrame(bubble, fg_color="transparent", height=8).pack()

    def _copy_template(self):
        """카카오 비즈센터 제출용 텍스트 복사"""
        body = self.body_editor.get("1.0", "end").strip()
        t = self.type_var.get()
        code = self.code_entry.get().strip()

        text = f"[템플릿 코드] {code}\n"
        text += f"[유형] {self.TEMPLATE_TYPES.get(t, t)}\n"
        text += f"[카테고리] {self.category_var.get()}\n"
        if t == "emphasize":
            text += f"[강조 제목] {self.emphasize_entry.get()}\n"
        text += f"\n[본문]\n{body}\n"

        if self.buttons_data:
            text += "\n[버튼]\n"
            for btn in self.buttons_data:
                if not btn["row"].winfo_exists():
                    continue
                bt = self.BUTTON_TYPES.get(btn["type"].get(), btn["type"].get())
                text += f"  - {btn['name'].get()} ({bt}): {btn['url'].get()}\n"

        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("복사 완료",
            "템플릿 텍스트가 클립보드에 복사되었습니다.\n"
            "카카오 비즈니스센터에 붙여넣기하여 검수 요청하세요.")

    # ══════════════════════════════════════
    #  가이드 탭
    # ══════════════════════════════════════

    def _build_guide_tab(self):
        tab = ctk.CTkScrollableFrame(self.tab_container, fg_color=T.BG_CARD,
                                      corner_radius=10,
                                      scrollbar_button_color=T.BG_HOVER)
        tab.grid(row=0, column=0, sticky="nsew")
        self.tabs["guide"] = tab

        pad = {"padx": 20, "anchor": "w"}

        def title(text):
            ctk.CTkLabel(tab, text=text, font=(T.get_font_family(), 16, "bold"),
                         text_color="#58a6ff").pack(**pad, pady=(20, 4))

        def subtitle(text):
            ctk.CTkLabel(tab, text=text, font=(T.get_font_family(), 13, "bold"),
                         text_color=T.TEXT_PRIMARY).pack(**pad, pady=(12, 4))

        def body(text):
            ctk.CTkLabel(tab, text=text, font=(T.get_font_family(), 11),
                         text_color=T.TEXT_SECONDARY, wraplength=700, justify="left"
                         ).pack(**pad, pady=(0, 4))

        def warn(text):
            frame = ctk.CTkFrame(tab, fg_color="#3a2a00", corner_radius=8)
            frame.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(frame, text=f"⚠ {text}", font=(T.get_font_family(), 11),
                         text_color="#d29922", wraplength=660, justify="left"
                         ).pack(padx=12, pady=8)

        def tip(text):
            frame = ctk.CTkFrame(tab, fg_color="#0a2a3a", corner_radius=8)
            frame.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(frame, text=f"💡 {text}", font=(T.get_font_family(), 11),
                         text_color="#58a6ff", wraplength=660, justify="left"
                         ).pack(padx=12, pady=8)

        # ─── 가이드 내용 ───

        title("알림톡 템플릿 제작 가이드")
        body("알림톡은 카카오톡을 통해 발송되는 정보성 메시지입니다.\n"
             "템플릿을 카카오 비즈니스센터에서 등록하고 검수 승인을 받아야 발송할 수 있습니다.")

        subtitle("1단계: 카카오 비즈니스센터 가입")
        body("① business.kakao.com 접속\n"
             "② 카카오 계정으로 로그인\n"
             "③ 비즈니스 채널 개설 (사업자등록증 필요)\n"
             "④ '알림톡' 서비스 신청")
        tip("사업자등록증이 있어야 알림톡 서비스를 신청할 수 있습니다.")

        subtitle("2단계: 발신 프로필 등록")
        body("① 비즈니스센터 > 알림톡 관리 > 발신프로필\n"
             "② 카카오톡 채널 연동\n"
             "③ 발신프로필 검수 요청 (영업일 1~2일)")

        subtitle("3단계: 템플릿 등록")
        body("① 비즈니스센터 > 알림톡 관리 > 템플릿 관리\n"
             "② '템플릿 등록' 클릭\n"
             "③ 아래 양식에 맞춰 작성")

        subtitle("  템플릿 유형 선택")
        body("• 기본형: 텍스트만 (가장 일반적)\n"
             "• 강조 표기형: 상단에 강조 제목 표시 (예: '결제 완료', '배송 시작')\n"
             "• 이미지형: 상단에 이미지 표시 (800x400px, jpg/png, 500KB 이하)\n"
             "• 아이템리스트형: 항목별 정보 나열 (주문내역 등)")
        warn("이미지형과 강조 표기형은 동시 사용 불가합니다.")

        subtitle("  변수 사용법")
        body("본문에 #{변수명} 형태로 삽입하면 발송 시 실제 값으로 치환됩니다.\n\n"
             "예시:\n"
             "  #{이름} → 홍길동\n"
             "  #{주문번호} → 20260313-001\n"
             "  #{금액} → 50,000원\n"
             "  #{날짜} → 2026.03.15\n"
             "  #{상품명} → 노트북 거치대\n"
             "  #{URL} → https://example.com/order/123")
        warn("변수만으로 이루어진 템플릿은 검수 반려됩니다.\n"
             "고정 텍스트와 변수를 적절히 혼합하세요.")

        subtitle("  버튼 설정")
        body("• 웹 링크 (WL): URL로 이동 (가장 많이 사용)\n"
             "• 앱 링크 (AL): 앱 스킴으로 앱 실행\n"
             "• 봇 키워드 (BK): 챗봇에 키워드 전송\n"
             "• 메시지 전달 (MD): 다른 사람에게 메시지 공유\n"
             "• 배송 조회 (DS): 배송 조회 링크\n"
             "• 채널 추가 (AC): 카카오톡 채널 추가 버튼")
        warn("버튼은 최대 5개까지 가능합니다.\n"
             "버튼명에 변수(#{})를 포함하면 검수 반려됩니다.")

        subtitle("4단계: 검수 요청")
        body("① 템플릿 작성 완료 후 '검수 요청' 클릭\n"
             "② 영업일 기준 2일 이내 승인/반려\n"
             "③ 반려 시 사유 확인 후 수정하여 재요청\n"
             "④ 승인되면 템플릿 코드 확인")

        subtitle("5단계: TalkPC에서 발송")
        body("① 승인된 템플릿 코드를 TalkPC 설정에 등록\n"
             "② 발송 화면에서 '알림톡' 선택\n"
             "③ 연락처 선택 → 변수값 자동 매핑 → 발송")
        tip("TalkPC의 '알림톡 디자이너'에서 미리 템플릿을 설계하고\n"
            "'텍스트 복사' 버튼으로 카카오 비즈센터에 붙여넣기하면 편리합니다.")

        subtitle("검수 승인 팁")
        body("✅ 정보성 메시지만 가능 (광고 불가)\n"
             "✅ 구매/예약/배송 등 거래 관련 안내\n"
             "✅ 인증번호, 비밀번호 변경 등 보안 알림\n"
             "✅ 고객이 요청한 정보 (견적서, 예약확인 등)")
        warn("❌ 할인 쿠폰, 이벤트 안내 → 친구톡 사용\n"
             "❌ 앱 설치 유도\n"
             "❌ 뉴스레터, 구독형 메시지\n"
             "❌ 불특정 다수 대상 공지")

        subtitle("과금 안내")
        body("• 알림톡 성공: 7원/건\n"
             "• 알림톡 실패 → SMS 대체발송: 8원/건\n"
             "• 알림톡 실패 → LMS 대체발송: 25원/건\n"
             "• 수신자가 카카오톡 미사용 시 대체발송 자동 처리")

        # 하단 여백
        ctk.CTkFrame(tab, fg_color="transparent", height=30).pack()

    # ══════════════════════════════════════
    #  탭 전환
    # ══════════════════════════════════════

    def _switch_tab(self, tab_id):
        for tid, tab in self.tabs.items():
            if tid == tab_id:
                tab.tkraise()
            self.tab_buttons[tid].configure(
                fg_color="#58a6ff" if tid == tab_id else T.BG_HOVER,
                text_color="#ffffff" if tid == tab_id else T.TEXT_PRIMARY
            )

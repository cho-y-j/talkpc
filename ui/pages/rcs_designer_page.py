"""RCS 메시지 디자이너 - 리치 메시지 설계 + 미리보기 + 가이드"""
import customtkinter as ctk
from tkinter import messagebox, filedialog
from ui.theme import AppTheme as T


class RCSDesignerPage(ctk.CTkFrame):
    """RCS 리치 메시지 설계 + 사용 가이드"""

    MSG_TYPES = {
        "standalone": "단독형 (텍스트+이미지+버튼)",
        "card": "카드형 (이미지+제목+설명+버튼)",
        "carousel": "캐러셀 (카드 여러장 슬라이드)",
    }

    BUTTON_TYPES = {
        "url": "URL 링크",
        "call": "전화 연결",
        "map": "지도 표시",
        "calendar": "캘린더 일정",
        "copy": "복사하기",
        "reply": "대화방 전송",
    }

    def __init__(self, parent, api_client=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color=T.BG_DARK)
        self.api_client = api_client
        self.buttons_data = []
        self.cards_data = []
        self.image_path = None
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 헤더
        header = ctk.CTkFrame(self, fg_color="transparent", height=40)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 8))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="RCS 메시지 디자이너",
                     font=(T.get_font_family(), 16, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(side="left")

        # 탭 버튼
        tab_frame = ctk.CTkFrame(header, fg_color="transparent")
        tab_frame.pack(side="right")
        self.tab_buttons = {}
        for tab_id, label in [("designer", "디자이너"), ("guide", "사용 가이드")]:
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

        # 메시지 유형
        ctk.CTkLabel(left, text="메시지 유형", font=(T.get_font_family(), 12, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(12, 4))
        self.type_var = ctk.StringVar(value="standalone")
        type_frame = ctk.CTkFrame(left, fg_color="transparent")
        type_frame.pack(fill="x", padx=16, pady=(0, 8))
        for val, label in self.MSG_TYPES.items():
            ctk.CTkRadioButton(type_frame, text=label, variable=self.type_var, value=val,
                               font=(T.get_font_family(), 11), text_color=T.TEXT_PRIMARY,
                               fg_color="#58a6ff", border_color=T.BORDER,
                               command=self._on_type_change
                               ).pack(anchor="w", pady=2)

        # 구분선
        ctk.CTkFrame(left, fg_color=T.BORDER, height=1).pack(fill="x", padx=16, pady=8)

        # ── 단독형 / 카드형 공통 에디터 ──
        self.standalone_frame = ctk.CTkFrame(left, fg_color="transparent")

        # 제목 (카드형)
        self.title_frame = ctk.CTkFrame(self.standalone_frame, fg_color="transparent")
        ctk.CTkLabel(self.title_frame, text="제목 (선택)",
                     font=(T.get_font_family(), 12, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w")
        self.title_entry = ctk.CTkEntry(self.title_frame,
                                         placeholder_text="카드 제목 (30자 이내)",
                                         font=(T.get_font_family(), 11),
                                         fg_color=T.BG_INPUT, border_color=T.BORDER,
                                         text_color=T.TEXT_PRIMARY, height=32)
        self.title_entry.pack(fill="x", pady=(4, 0))
        self.title_frame.pack(fill="x", padx=16, pady=(0, 8))

        # 이미지
        ctk.CTkLabel(self.standalone_frame, text="이미지 (선택, jpg/png)",
                     font=(T.get_font_family(), 12, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(0, 4))
        img_btn_frame = ctk.CTkFrame(self.standalone_frame, fg_color="transparent")
        img_btn_frame.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkButton(img_btn_frame, text="이미지 선택", width=100, height=28,
                      font=(T.get_font_family(), 10), fg_color=T.BG_HOVER,
                      hover_color=T.BORDER, text_color=T.TEXT_PRIMARY,
                      command=self._select_image).pack(side="left")
        self.img_label = ctk.CTkLabel(img_btn_frame, text="선택 안됨",
                                       font=(T.get_font_family(), 10),
                                       text_color=T.TEXT_MUTED)
        self.img_label.pack(side="left", padx=8)

        # 본문
        ctk.CTkLabel(self.standalone_frame, text="본문 메시지",
                     font=(T.get_font_family(), 12, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(0, 4))

        # 변수 삽입
        var_frame = ctk.CTkFrame(self.standalone_frame, fg_color="transparent")
        var_frame.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(var_frame, text="변수:", font=(T.get_font_family(), 10),
                     text_color=T.TEXT_MUTED).pack(side="left")
        for var in ["%이름%", "%주문번호%", "%금액%", "%날짜%", "%상품명%", "%URL%"]:
            ctk.CTkButton(var_frame, text=var, width=70, height=22,
                          font=(T.get_font_family(), 9), fg_color=T.BG_HOVER,
                          hover_color=T.BORDER, text_color="#58a6ff", corner_radius=4,
                          command=lambda v=var: self.body_editor.insert("insert", v)
                          ).pack(side="left", padx=2)

        self.body_editor = ctk.CTkTextbox(self.standalone_frame, height=180,
                                           font=(T.get_font_family(), 12),
                                           fg_color=T.BG_INPUT, text_color=T.TEXT_PRIMARY,
                                           corner_radius=6, border_width=1,
                                           border_color=T.BORDER)
        self.body_editor.pack(fill="x", padx=16, pady=(0, 4))
        self.body_editor.insert("1.0",
            "%이름%님 안녕하세요!\n\n"
            "주문하신 상품 배송이 시작되었습니다.\n\n"
            "주문번호: %주문번호%\n"
            "상품명: %상품명%\n"
            "배송시작: %날짜%\n\n"
            "감사합니다.")
        self.body_editor.bind("<KeyRelease>", lambda e: self._update_preview())

        self.char_count = ctk.CTkLabel(self.standalone_frame, text="0 / 1300자",
                                        font=(T.get_font_family(), 9),
                                        text_color=T.TEXT_MUTED)
        self.char_count.pack(anchor="e", padx=16)

        # 버튼 (최대 3개)
        ctk.CTkLabel(self.standalone_frame, text="버튼 (최대 3개)",
                     font=(T.get_font_family(), 12, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(8, 4))

        self.buttons_frame = ctk.CTkFrame(self.standalone_frame, fg_color="transparent")
        self.buttons_frame.pack(fill="x", padx=16, pady=(0, 4))

        add_btn_frame = ctk.CTkFrame(self.standalone_frame, fg_color="transparent")
        add_btn_frame.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkButton(add_btn_frame, text="+ 버튼 추가", width=100, height=28,
                      font=(T.get_font_family(), 10), fg_color="#1a3a5c",
                      hover_color="#2471a3", text_color="#58a6ff",
                      command=self._add_button).pack(side="left")

        self.standalone_frame.pack(fill="x")

        # 초기 버튼 1개
        self._add_button()

        # ── 캐러셀 에디터 ──
        self.carousel_frame = ctk.CTkFrame(left, fg_color="transparent")

        ctk.CTkLabel(self.carousel_frame, text="캐러셀 카드 (최대 6장)",
                     font=(T.get_font_family(), 12, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(0, 8))

        self.carousel_cards_frame = ctk.CTkFrame(self.carousel_frame, fg_color="transparent")
        self.carousel_cards_frame.pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkButton(self.carousel_frame, text="+ 카드 추가", width=100, height=28,
                      font=(T.get_font_family(), 10), fg_color="#1a3a5c",
                      hover_color="#2471a3", text_color="#58a6ff",
                      command=self._add_carousel_card).pack(anchor="w", padx=16, pady=(0, 12))

        # 기본 캐러셀 카드 2장
        self._add_carousel_card("상품 A", "첫 번째 카드 내용입니다.\n가격: 29,900원")
        self._add_carousel_card("상품 B", "두 번째 카드 내용입니다.\n가격: 39,900원")

        # ── 우측: 미리보기 ──
        right = ctk.CTkFrame(tab, fg_color=T.BG_CARD, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="RCS 메시지 미리보기",
                     font=(T.get_font_family(), 13, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(padx=16, pady=(12, 8), anchor="w")

        # 폰 프레임
        phone = ctk.CTkFrame(right, fg_color="#1a1a2e", corner_radius=20,
                              width=320, height=520)
        phone.pack(padx=20, pady=(0, 12))
        phone.pack_propagate(False)

        # 메시지 앱 헤더
        msg_header = ctk.CTkFrame(phone, fg_color="#16213e", height=40, corner_radius=0)
        msg_header.pack(fill="x")
        msg_header.pack_propagate(False)
        ctk.CTkLabel(msg_header, text="메시지",
                     font=(T.get_font_family(), 12, "bold"),
                     text_color="#e0e0e0").pack(side="left", padx=12, pady=8)
        ctk.CTkLabel(msg_header, text="RCS",
                     font=(T.get_font_family(), 9),
                     text_color="#58a6ff").pack(side="right", padx=12, pady=8)

        # 메시지 영역
        self.preview_area = ctk.CTkScrollableFrame(phone, fg_color="#1a1a2e",
                                                    scrollbar_button_color="#2a2a4e")
        self.preview_area.pack(fill="both", expand=True, padx=8, pady=8)

        # 하단: 복사/갱신
        bottom = ctk.CTkFrame(right, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkButton(bottom, text="메시지 텍스트 복사", width=140, height=30,
                      font=(T.get_font_family(), 11), fg_color="#58a6ff",
                      hover_color="#4090e0", text_color="#ffffff",
                      command=self._copy_template).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bottom, text="미리보기 갱신", width=100, height=30,
                      font=(T.get_font_family(), 11), fg_color=T.BG_HOVER,
                      hover_color=T.BORDER, text_color=T.TEXT_PRIMARY,
                      command=self._update_preview).pack(side="left")

        # 단가 안내
        ctk.CTkLabel(right, text="RCS 단가: SMS 12원, LMS 30원, MMS 50원/건",
                     font=(T.get_font_family(), 10), text_color=T.TEXT_MUTED
                     ).pack(padx=16, pady=(0, 8))

        self._update_preview()

    # ── 버튼 관리 ──

    def _add_button(self):
        if len(self.buttons_data) >= 3:
            return
        idx = len(self.buttons_data)
        row = ctk.CTkFrame(self.buttons_frame, fg_color=T.BG_INPUT, corner_radius=6)
        row.pack(fill="x", pady=2)

        type_var = ctk.StringVar(value="url")
        ctk.CTkComboBox(row, values=list(self.BUTTON_TYPES.keys()),
                        variable=type_var, width=80, height=26,
                        font=(T.get_font_family(), 9), fg_color=T.BG_DARK,
                        border_color=T.BORDER, text_color=T.TEXT_PRIMARY,
                        dropdown_fg_color=T.BG_CARD).pack(side="left", padx=4, pady=4)

        name_entry = ctk.CTkEntry(row, placeholder_text="버튼명",
                                   font=(T.get_font_family(), 10), width=100, height=26,
                                   fg_color=T.BG_DARK, border_color=T.BORDER,
                                   text_color=T.TEXT_PRIMARY)
        name_entry.pack(side="left", padx=2, pady=4)
        name_entry.insert(0, "자세히 보기" if idx == 0 else "")

        url_entry = ctk.CTkEntry(row, placeholder_text="URL / 전화번호",
                                  font=(T.get_font_family(), 10), height=26,
                                  fg_color=T.BG_DARK, border_color=T.BORDER,
                                  text_color=T.TEXT_PRIMARY)
        url_entry.pack(side="left", fill="x", expand=True, padx=2, pady=4)
        url_entry.insert(0, "https://" if idx == 0 else "")

        ctk.CTkButton(row, text="✕", width=24, height=24,
                      font=(T.get_font_family(), 10), fg_color="transparent",
                      hover_color=T.ERROR, text_color=T.TEXT_MUTED,
                      command=lambda r=row: self._remove_button(r)
                      ).pack(side="right", padx=4, pady=4)

        self.buttons_data.append({"row": row, "type": type_var,
                                   "name": name_entry, "url": url_entry})

    def _remove_button(self, row):
        row.destroy()
        self.buttons_data = [b for b in self.buttons_data if b["row"].winfo_exists()]

    # ── 캐러셀 카드 관리 ──

    def _add_carousel_card(self, default_title="", default_desc=""):
        if len(self.cards_data) >= 6:
            return
        idx = len(self.cards_data)
        card = ctk.CTkFrame(self.carousel_cards_frame, fg_color=T.BG_INPUT,
                             corner_radius=8, border_width=1, border_color=T.BORDER)
        card.pack(fill="x", pady=4)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(header, text=f"카드 {idx + 1}",
                     font=(T.get_font_family(), 11, "bold"),
                     text_color="#58a6ff").pack(side="left")
        ctk.CTkButton(header, text="✕", width=24, height=24,
                      font=(T.get_font_family(), 10), fg_color="transparent",
                      hover_color=T.ERROR, text_color=T.TEXT_MUTED,
                      command=lambda c=card: self._remove_card(c)
                      ).pack(side="right")

        # 카드 제목
        title_entry = ctk.CTkEntry(card, placeholder_text="카드 제목",
                                    font=(T.get_font_family(), 11),
                                    fg_color=T.BG_DARK, border_color=T.BORDER,
                                    text_color=T.TEXT_PRIMARY, height=28)
        title_entry.pack(fill="x", padx=10, pady=2)
        if default_title:
            title_entry.insert(0, default_title)

        # 카드 설명
        desc_editor = ctk.CTkTextbox(card, height=60,
                                      font=(T.get_font_family(), 11),
                                      fg_color=T.BG_DARK, text_color=T.TEXT_PRIMARY,
                                      corner_radius=4, border_width=1,
                                      border_color=T.BORDER)
        desc_editor.pack(fill="x", padx=10, pady=2)
        if default_desc:
            desc_editor.insert("1.0", default_desc)

        # 카드 버튼명
        btn_entry = ctk.CTkEntry(card, placeholder_text="버튼명 (예: 구매하기)",
                                  font=(T.get_font_family(), 10),
                                  fg_color=T.BG_DARK, border_color=T.BORDER,
                                  text_color=T.TEXT_PRIMARY, height=26)
        btn_entry.pack(fill="x", padx=10, pady=(2, 8))
        btn_entry.insert(0, "자세히 보기")

        self.cards_data.append({
            "card": card, "title": title_entry,
            "desc": desc_editor, "btn": btn_entry
        })

    def _remove_card(self, card):
        card.destroy()
        self.cards_data = [c for c in self.cards_data if c["card"].winfo_exists()]

    # ── 이벤트 ──

    def _on_type_change(self):
        t = self.type_var.get()
        self.standalone_frame.pack_forget()
        self.carousel_frame.pack_forget()
        if t in ("standalone", "card"):
            self.standalone_frame.pack(fill="x")
            if t == "card":
                self.title_frame.pack(fill="x", padx=16, pady=(0, 8))
            else:
                self.title_frame.pack_forget()
        elif t == "carousel":
            self.carousel_frame.pack(fill="x")
        self._update_preview()

    def _select_image(self):
        fp = filedialog.askopenfilename(
            filetypes=[("이미지", "*.jpg *.jpeg *.png")])
        if fp:
            import os
            self.image_path = fp
            self.img_label.configure(text=os.path.basename(fp), text_color="#58a6ff")
            self._update_preview()

    # ── 미리보기 ──

    def _update_preview(self):
        for w in self.preview_area.winfo_children():
            w.destroy()

        t = self.type_var.get()

        if t == "carousel":
            self._preview_carousel()
        else:
            self._preview_standalone()

    def _preview_standalone(self):
        body = self.body_editor.get("1.0", "end").strip()
        t = self.type_var.get()

        # 글자 수
        self.char_count.configure(text=f"{len(body)} / 1300자",
                                   text_color=T.ERROR if len(body) > 1300 else T.TEXT_MUTED)

        # 변수 치환
        preview = body.replace("%이름%", "홍길동").replace("%주문번호%", "20260313-001")
        preview = preview.replace("%금액%", "50,000원").replace("%날짜%", "2026.03.15")
        preview = preview.replace("%상품명%", "테스트 상품").replace("%URL%", "example.com")

        # RCS 말풍선
        bubble = ctk.CTkFrame(self.preview_area, fg_color="#2a2a4e",
                               corner_radius=12, border_width=1, border_color="#3a3a6e")
        bubble.pack(fill="x", pady=4, padx=4)

        # 발신자
        prof = ctk.CTkFrame(bubble, fg_color="transparent")
        prof.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(prof, text="TalkPC", font=(T.get_font_family(), 11, "bold"),
                     text_color="#e0e0e0").pack(side="left")
        ctk.CTkLabel(prof, text="RCS", font=(T.get_font_family(), 9),
                     text_color="#58a6ff").pack(side="left", padx=6)

        # 이미지 플레이스홀더
        if self.image_path or t == "card":
            img_holder = ctk.CTkFrame(bubble, fg_color="#3a3a5e",
                                       height=100, corner_radius=8)
            img_holder.pack(fill="x", padx=10, pady=(4, 0))
            img_holder.pack_propagate(False)
            lbl = self.image_path.split("/")[-1] if self.image_path else "이미지 영역"
            ctk.CTkLabel(img_holder, text=f"🖼 {lbl}",
                         font=(T.get_font_family(), 10),
                         text_color="#8888aa").pack(expand=True)

        # 제목 (카드형)
        if t == "card":
            title_text = self.title_entry.get() or "카드 제목"
            ctk.CTkLabel(bubble, text=title_text,
                         font=(T.get_font_family(), 14, "bold"),
                         text_color="#e0e0e0", wraplength=260
                         ).pack(fill="x", padx=12, pady=(8, 0))

        # 본문
        ctk.CTkLabel(bubble, text=preview,
                     font=(T.get_font_family(), 11),
                     text_color="#c0c0d0", wraplength=260, justify="left"
                     ).pack(fill="x", padx=12, pady=8)

        # 버튼들
        for btn in self.buttons_data:
            if not btn["row"].winfo_exists():
                continue
            name = btn["name"].get() or "버튼"
            ctk.CTkButton(bubble, text=name, height=30,
                          font=(T.get_font_family(), 11),
                          fg_color="#3a3a6e", hover_color="#4a4a8e",
                          text_color="#58a6ff", corner_radius=6,
                          border_width=1, border_color="#4a4a8e"
                          ).pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkFrame(bubble, fg_color="transparent", height=6).pack()

    def _preview_carousel(self):
        """캐러셀 미리보기"""
        for card_data in self.cards_data:
            if not card_data["card"].winfo_exists():
                continue

            card = ctk.CTkFrame(self.preview_area, fg_color="#2a2a4e",
                                 corner_radius=12, border_width=1, border_color="#3a3a6e")
            card.pack(fill="x", pady=4, padx=4)

            # 이미지 영역
            img_holder = ctk.CTkFrame(card, fg_color="#3a3a5e",
                                       height=80, corner_radius=8)
            img_holder.pack(fill="x", padx=8, pady=(8, 0))
            img_holder.pack_propagate(False)
            ctk.CTkLabel(img_holder, text="🖼 카드 이미지",
                         font=(T.get_font_family(), 10),
                         text_color="#8888aa").pack(expand=True)

            # 제목
            title = card_data["title"].get() or "카드 제목"
            ctk.CTkLabel(card, text=title,
                         font=(T.get_font_family(), 13, "bold"),
                         text_color="#e0e0e0", wraplength=260
                         ).pack(fill="x", padx=10, pady=(6, 0))

            # 설명
            desc = card_data["desc"].get("1.0", "end").strip()
            if desc:
                ctk.CTkLabel(card, text=desc,
                             font=(T.get_font_family(), 10),
                             text_color="#a0a0b0", wraplength=260, justify="left"
                             ).pack(fill="x", padx=10, pady=(2, 0))

            # 버튼
            btn_name = card_data["btn"].get() or "버튼"
            ctk.CTkButton(card, text=btn_name, height=28,
                          font=(T.get_font_family(), 10),
                          fg_color="#3a3a6e", hover_color="#4a4a8e",
                          text_color="#58a6ff", corner_radius=6,
                          border_width=1, border_color="#4a4a8e"
                          ).pack(fill="x", padx=8, pady=(6, 8))

    # ── 복사 ──

    def _copy_template(self):
        t = self.type_var.get()
        text = f"[RCS 메시지 유형] {self.MSG_TYPES.get(t, t)}\n"

        if t == "carousel":
            for i, cd in enumerate(self.cards_data):
                if not cd["card"].winfo_exists():
                    continue
                text += f"\n--- 카드 {i + 1} ---\n"
                text += f"제목: {cd['title'].get()}\n"
                text += f"내용: {cd['desc'].get('1.0', 'end').strip()}\n"
                text += f"버튼: {cd['btn'].get()}\n"
        else:
            body = self.body_editor.get("1.0", "end").strip()
            if t == "card":
                text += f"[제목] {self.title_entry.get()}\n"
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
            "RCS 메시지 텍스트가 클립보드에 복사되었습니다.")

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

        title("RCS 메시지 사용 가이드")
        body("RCS(Rich Communication Services)는 기존 SMS/MMS를 대체하는 차세대 메시지 규격입니다.\n"
             "텍스트, 이미지, 버튼, 카드, 캐러셀 등 풍부한 콘텐츠를 문자 앱에서 바로 표시합니다.\n"
             "별도 앱 설치 없이 기본 메시지 앱에서 수신됩니다.")

        subtitle("RCS vs 알림톡 vs SMS 비교")
        body("┌─────────┬──────────┬──────────┬──────────┐\n"
             "│  구분     │  SMS/LMS  │  알림톡    │  RCS      │\n"
             "├─────────┼──────────┼──────────┼──────────┤\n"
             "│  플랫폼   │  모든 폰   │  카카오톡  │  안드로이드 │\n"
             "│  이미지   │  MMS만    │  제한적    │  자유롭게   │\n"
             "│  버튼     │  불가     │  최대 5개  │  최대 4개  │\n"
             "│  카드/슬라이드│  불가  │  불가      │  가능      │\n"
             "│  사전검수  │  불필요   │  필수      │  불필요    │\n"
             "│  대체발송  │  -       │  SMS 가능  │  SMS 자동  │\n"
             "└─────────┴──────────┴──────────┴──────────┘")
        tip("RCS는 사전 검수 없이 자유롭게 메시지를 디자인하여 발송할 수 있습니다.\n"
            "다만 iPhone에서는 수신이 불가하며, SMS로 대체발송됩니다.")

        subtitle("1단계: RCS 브랜드 등록")
        body("① 세종텔레콤을 통해 RCS 서비스 신청\n"
             "② 사업자 정보 및 브랜드 정보 제출\n"
             "③ 브랜드 키(brand_key) 및 챗봇 ID(chatbot_id) 발급\n"
             "④ TalkPC 서버 설정에 브랜드 정보 등록")
        warn("RCS 브랜드 등록은 세종텔레콤 영업 담당을 통해 진행됩니다.\n"
             "등록 완료까지 영업일 2~5일 소요됩니다.")

        subtitle("2단계: 메시지 유형 선택")
        body("RCS는 3가지 메시지 유형을 지원합니다:")

        subtitle("  단독형 메시지")
        body("• 텍스트 + 이미지(선택) + 버튼(최대 3개)\n"
             "• 일반 알림, 공지, 안내 메시지에 적합\n"
             "• SMS/LMS와 비슷하지만 버튼과 이미지 추가 가능\n"
             "• 본문 최대 1,300자")

        subtitle("  카드형 메시지")
        body("• 이미지 + 제목 + 설명 + 버튼(최대 3개)\n"
             "• 상품 소개, 이벤트 안내에 적합\n"
             "• 시각적으로 돋보이는 카드 형태 레이아웃")

        subtitle("  캐러셀 메시지")
        body("• 카드 여러 장을 좌우로 슬라이드\n"
             "• 최대 6장의 카드 구성 가능\n"
             "• 여러 상품 비교, 메뉴 안내 등에 적합\n"
             "• 각 카드마다 이미지 + 제목 + 설명 + 버튼")
        tip("캐러셀은 쇼핑몰 상품 추천, 레스토랑 메뉴 안내 등에\n"
            "가장 효과적인 메시지 형태입니다.")

        subtitle("3단계: 버튼 설정")
        body("• URL 링크: 웹사이트로 이동 (가장 많이 사용)\n"
             "• 전화 연결: 전화번호로 바로 통화\n"
             "• 지도 표시: 위치 정보 표시\n"
             "• 캘린더 일정: 일정 추가\n"
             "• 복사하기: 텍스트 복사 (쿠폰번호 등)\n"
             "• 대화방 전송: 메시지 공유")
        warn("버튼은 메시지 유형에 따라 최대 3~4개까지 추가 가능합니다.")

        subtitle("4단계: 변수 활용")
        body("본문에 %변수명% 형태로 변수를 삽입하면\n"
             "발송 시 연락처의 실제 정보로 자동 치환됩니다.\n\n"
             "지원 변수:\n"
             "  %이름% → 홍길동\n"
             "  %주문번호% → 20260313-001\n"
             "  %금액% → 50,000원\n"
             "  %날짜% → 2026.03.15\n"
             "  %상품명% → 노트북 거치대\n"
             "  %URL% → https://example.com")

        subtitle("5단계: 발송")
        body("① 디자이너에서 메시지 설계 완료\n"
             "② 발송 화면에서 'RCS' 선택\n"
             "③ 연락처 선택 → 변수값 자동 매핑\n"
             "④ 미리보기 확인 후 발송\n"
             "⑤ 수신자가 iPhone이면 자동으로 SMS 대체발송")

        subtitle("대체발송 (Fallback)")
        body("RCS 메시지를 수신할 수 없는 경우 자동으로 대체발송됩니다:\n\n"
             "• iPhone 사용자 → SMS/LMS 대체발송\n"
             "• 기기가 RCS 미지원 → SMS/LMS 대체발송\n"
             "• 데이터 연결 없음 → SMS/LMS 대체발송\n\n"
             "대체발송 시 텍스트 본문만 전송됩니다 (이미지, 버튼 제외).")
        warn("대체발송된 메시지는 SMS/LMS 요금이 별도 적용됩니다.")

        subtitle("과금 안내")
        body("• RCS SMS (90바이트 이하): 12원/건\n"
             "• RCS LMS (90바이트 초과): 30원/건\n"
             "• RCS MMS (이미지 포함): 50원/건\n"
             "• 대체발송 SMS: 8원/건\n"
             "• 대체발송 LMS: 25원/건\n\n"
             "※ 단가는 관리자 설정에서 변경 가능합니다.")

        subtitle("주의사항")
        body("• RCS는 안드로이드 기기에서만 수신 가능\n"
             "• 수신자의 기본 메시지 앱이 Google 메시지 또는 삼성 메시지여야 함\n"
             "• 이미지 크기: 가로 최대 1440px, 세로 제한 없음\n"
             "• 이미지 용량: 1MB 이하 권장\n"
             "• 광고성 메시지는 080 수신거부 번호 필수 (야간 발송 불가)")
        tip("수신자 중 iPhone 비율이 높다면 알림톡을 함께 활용하는 것이 효과적입니다.\n"
            "알림톡은 카카오톡이 설치된 모든 기기에서 수신 가능합니다.")

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

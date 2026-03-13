"""충전하기 페이지 - 금액 선택 + 결제 (추후 API 연동)"""
import customtkinter as ctk
from ui.theme import AppTheme as T


class ChargePage(ctk.CTkFrame):
    """크레딧 충전 페이지"""

    AMOUNTS = [
        (10000, "1만원"),
        (50000, "5만원"),
        (100000, "10만원"),
        (500000, "50만원"),
        (1000000, "100만원"),
    ]

    def __init__(self, parent, api_client=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color=T.BG_DARK)
        self.api_client = api_client
        self.selected_amount = None
        self.amount_buttons = []
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 헤더
        header = ctk.CTkFrame(self, fg_color="transparent", height=40)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 8))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="충전하기",
                     font=(T.get_font_family(), 16, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(side="left")

        # 메인 콘텐츠 (가운데 정렬)
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 16))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(3, weight=1)

        # ── 현재 잔액 ──
        balance_card = ctk.CTkFrame(content, fg_color=T.BG_CARD,
                                     corner_radius=10, border_width=1,
                                     border_color=T.BORDER)
        balance_card.grid(row=0, column=0, sticky="ew", pady=(0, 16))

        balance_inner = ctk.CTkFrame(balance_card, fg_color="transparent")
        balance_inner.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(balance_inner, text="현재 잔액",
                     font=(T.get_font_family(), 11),
                     text_color=T.TEXT_MUTED).pack(anchor="w")

        self.balance_label = ctk.CTkLabel(
            balance_inner, text="- 원",
            font=(T.get_font_family(), 28, "bold"),
            text_color="#58a6ff"
        )
        self.balance_label.pack(anchor="w", pady=(4, 0))

        # ── 충전 금액 선택 ──
        amount_card = ctk.CTkFrame(content, fg_color=T.BG_CARD,
                                    corner_radius=10, border_width=1,
                                    border_color=T.BORDER)
        amount_card.grid(row=1, column=0, sticky="ew", pady=(0, 16))

        amount_inner = ctk.CTkFrame(amount_card, fg_color="transparent")
        amount_inner.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(amount_inner, text="충전 금액 선택",
                     font=(T.get_font_family(), 13, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", pady=(0, 12))

        # 금액 버튼 그리드
        btn_frame = ctk.CTkFrame(amount_inner, fg_color="transparent")
        btn_frame.pack(fill="x")
        btn_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="amt")

        for i, (amount, label) in enumerate(self.AMOUNTS):
            btn = ctk.CTkButton(
                btn_frame, text=f"{label}\n({amount:,}원)",
                width=0, height=70, corner_radius=10,
                font=(T.get_font_family(), 13, "bold"),
                fg_color=T.BG_INPUT,
                hover_color=T.BG_HOVER,
                text_color=T.TEXT_SECONDARY,
                border_width=2, border_color=T.BORDER,
                command=lambda a=amount, idx=i: self._select_amount(a, idx)
            )
            btn.grid(row=0, column=i, padx=4, sticky="ew")
            self.amount_buttons.append(btn)

        # 선택된 금액 표시
        self.selected_label = ctk.CTkLabel(
            amount_inner, text="",
            font=(T.get_font_family(), 11),
            text_color=T.TEXT_MUTED
        )
        self.selected_label.pack(anchor="w", pady=(12, 0))

        # ── 결제 수단 ──
        pay_card = ctk.CTkFrame(content, fg_color=T.BG_CARD,
                                 corner_radius=10, border_width=1,
                                 border_color=T.BORDER)
        pay_card.grid(row=2, column=0, sticky="ew", pady=(0, 16))

        pay_inner = ctk.CTkFrame(pay_card, fg_color="transparent")
        pay_inner.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(pay_inner, text="결제 수단",
                     font=(T.get_font_family(), 13, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", pady=(0, 12))

        # 결제 방법 선택
        self.pay_method = ctk.StringVar(value="card")
        methods_frame = ctk.CTkFrame(pay_inner, fg_color="transparent")
        methods_frame.pack(fill="x")

        methods = [
            ("card", "신용/체크카드"),
            ("bank", "계좌이체"),
            ("virtual", "가상계좌"),
        ]

        for val, label in methods:
            rb = ctk.CTkRadioButton(
                methods_frame, text=label, variable=self.pay_method,
                value=val,
                font=(T.get_font_family(), 12),
                text_color=T.TEXT_PRIMARY,
                fg_color="#58a6ff",
                border_color=T.BORDER,
                hover_color=T.BG_HOVER,
            )
            rb.pack(side="left", padx=(0, 24), pady=4)

        # 안내 문구
        ctk.CTkLabel(pay_inner,
                     text="* 결제 수단 연동 준비 중입니다. 계좌 송금 후 관리자에게 문의해주세요.",
                     font=(T.get_font_family(), 10),
                     text_color=T.WARNING).pack(anchor="w", pady=(12, 0))

        # 계좌 정보
        account_frame = ctk.CTkFrame(pay_inner, fg_color=T.BG_INPUT,
                                      corner_radius=8)
        account_frame.pack(fill="x", pady=(8, 0))

        account_inner = ctk.CTkFrame(account_frame, fg_color="transparent")
        account_inner.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(account_inner, text="입금 계좌 안내",
                     font=(T.get_font_family(), 11, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(account_inner,
                     text="국민은행  000-0000-0000-00  (주)톡피씨",
                     font=(T.get_font_family(), 12),
                     text_color="#58a6ff").pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(account_inner,
                     text="입금 후 관리자에게 연락 시 즉시 충전됩니다.",
                     font=(T.get_font_family(), 10),
                     text_color=T.TEXT_MUTED).pack(anchor="w", pady=(2, 0))

        # ── 결제 버튼 ──
        bottom_frame = ctk.CTkFrame(content, fg_color="transparent")
        bottom_frame.grid(row=3, column=0, sticky="new", pady=(0, 16))

        self.pay_btn = ctk.CTkButton(
            bottom_frame, text="결제하기",
            width=200, height=48, corner_radius=10,
            font=(T.get_font_family(), 15, "bold"),
            fg_color=T.BG_HOVER, text_color=T.TEXT_MUTED,
            hover_color=T.BG_HOVER,
            state="disabled",
            command=self._on_pay
        )
        self.pay_btn.pack(pady=(0, 8))

        self.pay_status = ctk.CTkLabel(
            bottom_frame, text="",
            font=(T.get_font_family(), 11),
            text_color=T.TEXT_MUTED
        )
        self.pay_status.pack()

        # ── 충전 내역 ──
        history_card = ctk.CTkFrame(content, fg_color=T.BG_CARD,
                                     corner_radius=10, border_width=1,
                                     border_color=T.BORDER)
        content.grid_rowconfigure(4, weight=1)
        history_card.grid(row=4, column=0, sticky="nsew")
        history_card.grid_columnconfigure(0, weight=1)
        history_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(history_card, text="충전 내역",
                     font=(T.get_font_family(), 13, "bold"),
                     text_color=T.TEXT_PRIMARY).grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 0))

        self.history_scroll = ctk.CTkScrollableFrame(
            history_card, fg_color="transparent",
            scrollbar_button_color=T.BG_HOVER,
            scrollbar_button_hover_color=T.BORDER,
        )
        self.history_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 12))

    def _select_amount(self, amount: int, index: int):
        """금액 선택"""
        self.selected_amount = amount
        for i, btn in enumerate(self.amount_buttons):
            if i == index:
                btn.configure(fg_color="#1a3a5c", border_color="#58a6ff",
                              text_color="#58a6ff")
            else:
                btn.configure(fg_color=T.BG_INPUT, border_color=T.BORDER,
                              text_color=T.TEXT_SECONDARY)

        self.selected_label.configure(
            text=f"선택한 금액: {amount:,}원",
            text_color="#58a6ff"
        )

        # 결제 버튼 활성화
        self.pay_btn.configure(
            text=f"{amount:,}원 결제하기",
            fg_color="#58a6ff", text_color="#ffffff",
            hover_color="#4090e0",
            state="normal"
        )

    def _on_pay(self):
        """결제 버튼 클릭 (추후 결제 API 연동)"""
        if not self.selected_amount:
            return

        amount = self.selected_amount
        method = self.pay_method.get()
        method_name = {"card": "카드", "bank": "계좌이체", "virtual": "가상계좌"}.get(method, method)

        # TODO: 결제 API 호출
        # result = self.api_client.request_payment(amount, method)

        self.pay_status.configure(
            text=f"결제 기능 준비 중입니다. 계좌 송금 후 관리자에게 문의해주세요.",
            text_color=T.WARNING
        )

    def refresh(self):
        """잔액 + 충전 내역 새로고침"""
        if not self.api_client or not self.api_client.is_logged_in:
            return

        try:
            # 잔액
            balance = self.api_client.get_balance()
            self.balance_label.configure(text=f"{balance:,}원")

            # 충전 내역
            for w in self.history_scroll.winfo_children():
                w.destroy()

            history = self.api_client.get_credit_history()
            charges = [h for h in history if h.get("type") in ("charge", "bonus")]

            if not charges:
                ctk.CTkLabel(self.history_scroll, text="충전 내역이 없습니다",
                             font=(T.get_font_family(), 12),
                             text_color=T.TEXT_MUTED).pack(pady=20)
                return

            for i, item in enumerate(charges[:20]):
                bg = T.BG_INPUT if i % 2 == 0 else "transparent"
                row = ctk.CTkFrame(self.history_scroll, fg_color=bg,
                                   corner_radius=4, height=32)
                row.pack(fill="x", pady=1)
                row.pack_propagate(False)

                created = item.get("created_at", "")
                time_str = created[5:16].replace("T", " ") if len(created) >= 16 else created
                ctk.CTkLabel(row, text=time_str,
                             font=(T.get_font_family(), 10),
                             text_color=T.TEXT_SECONDARY, width=130, anchor="w"
                             ).pack(side="left", padx=(10, 0))

                type_label = "충전" if item.get("type") == "charge" else "보너스"
                type_color = T.SUCCESS if item.get("type") == "charge" else "#bc8cff"
                ctk.CTkLabel(row, text=type_label,
                             font=(T.get_font_family(), 10, "bold"),
                             text_color=type_color, width=60, anchor="w"
                             ).pack(side="left")

                amount = item.get("amount", 0)
                ctk.CTkLabel(row, text=f"+{amount:,}원",
                             font=(T.get_font_family(), 11, "bold"),
                             text_color=T.SUCCESS, width=100, anchor="w"
                             ).pack(side="left")

                desc = item.get("description", "")
                ctk.CTkLabel(row, text=desc,
                             font=(T.get_font_family(), 10),
                             text_color=T.TEXT_MUTED, anchor="w"
                             ).pack(side="left", fill="x", expand=True)

        except Exception:
            self.balance_label.configure(text="연결 오류")

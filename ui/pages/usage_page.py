"""사용량/잔액 페이지"""
import customtkinter as ctk
from ui.theme import AppTheme as T


class UsagePage(ctk.CTkFrame):
    """사용량 + 잔액 확인 페이지"""

    def __init__(self, parent, api_client=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color=T.BG_DARK)
        self.api_client = api_client
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 헤더
        header = ctk.CTkFrame(self, fg_color="transparent", height=50)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        ctk.CTkLabel(header, text="사용량 / 잔액",
                     font=(T.get_font_family(), 18, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(side="left")
        ctk.CTkButton(header, text="새로고침", width=80, height=32,
                      fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                      command=self.refresh).pack(side="right")

        # 메인 콘텐츠
        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        content.grid_columnconfigure((0, 1, 2), weight=1)

        # 잔액 카드
        balance_card = ctk.CTkFrame(content, fg_color=T.ACCENT, corner_radius=12, height=120)
        balance_card.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        balance_card.grid_propagate(False)
        balance_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(balance_card, text="현재 잔액", font=(T.get_font_family(), 12),
                     text_color="#cccccc").grid(row=0, column=0, pady=(15, 0))
        self.balance_label = ctk.CTkLabel(balance_card, text="- 원",
                                          font=(T.get_font_family(), 32, "bold"),
                                          text_color="#eeeeee")
        self.balance_label.grid(row=1, column=0, pady=(0, 15))

        # 오늘 사용량
        today_card = self._make_stat_card(content, "오늘")
        today_card.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=5)
        self.today_count = today_card.count_label
        self.today_cost = today_card.cost_label

        # 이번 달 사용량
        month_card = self._make_stat_card(content, "이번 달")
        month_card.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self.month_count = month_card.count_label
        self.month_cost = month_card.cost_label

        # 전체 통계
        total_card = self._make_stat_card(content, "전체")
        total_card.grid(row=1, column=2, sticky="nsew", padx=(5, 0), pady=5)
        self.total_count = total_card.count_label
        self.total_cost = total_card.cost_label

        # 발송 이력
        history_frame = ctk.CTkFrame(content, fg_color=T.BG_CARD, corner_radius=12)
        history_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(15, 0))
        ctk.CTkLabel(history_frame, text="최근 발송 이력",
                     font=(T.get_font_family(), 14, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(anchor="w", padx=15, pady=(15, 10))

        self.history_frame = ctk.CTkFrame(history_frame, fg_color="transparent")
        self.history_frame.pack(fill="both", padx=15, pady=(0, 15))

    def _make_stat_card(self, parent, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=T.BG_CARD, corner_radius=12)
        ctk.CTkLabel(card, text=title, font=(T.get_font_family(), 12),
                     text_color=T.TEXT_MUTED).pack(pady=(15, 5))
        card.count_label = ctk.CTkLabel(card, text="-건",
                                        font=(T.get_font_family(), 22, "bold"),
                                        text_color=T.TEXT_PRIMARY)
        card.count_label.pack()
        card.cost_label = ctk.CTkLabel(card, text="-원",
                                       font=(T.get_font_family(), 13),
                                       text_color=T.TEXT_SECONDARY)
        card.cost_label.pack(pady=(0, 15))
        return card

    def refresh(self):
        """서버에서 데이터 가져와 갱신"""
        if not self.api_client or not self.api_client.is_logged_in:
            return

        try:
            # 오늘 사용량 + 잔액
            daily = self.api_client.get_daily_usage()
            self.balance_label.configure(text=f"{daily.get('balance', 0):,}원")
            self.today_count.configure(text=f"{daily.get('count', 0):,}건")
            self.today_cost.configure(text=f"{daily.get('cost', 0):,}원")

            # 이번 달
            monthly = self.api_client.get_monthly_usage()
            self.month_count.configure(text=f"{monthly.get('count', 0):,}건")
            self.month_cost.configure(text=f"{monthly.get('cost', 0):,}원")

            # 전체 통계
            stats = self.api_client.get_usage_stats()
            self.total_count.configure(text=f"{stats.get('total_count', 0):,}건")
            self.total_cost.configure(text=f"{stats.get('total_cost', 0):,}원")

            # 최근 발송 이력
            history = self.api_client.get_send_history(page=1, size=20)
            for w in self.history_frame.winfo_children():
                w.destroy()

            if not history:
                ctk.CTkLabel(self.history_frame, text="발송 기록이 없습니다",
                             text_color=T.TEXT_MUTED).pack(pady=20)
                return

            for item in history:
                row = ctk.CTkFrame(self.history_frame, fg_color=T.BG_HOVER,
                                   corner_radius=6, height=36)
                row.pack(fill="x", pady=2)
                row.pack_propagate(False)

                ctk.CTkLabel(row, text=item.get("created_at", "")[:16],
                             font=(T.get_font_family(), 10),
                             text_color=T.TEXT_MUTED, width=120).pack(side="left", padx=8)
                ctk.CTkLabel(row, text=item.get("contact_name", "-"),
                             font=(T.get_font_family(), 11),
                             text_color=T.TEXT_PRIMARY, width=80).pack(side="left")

                msg_type = item.get("msg_type", "")
                type_color = T.ACCENT if msg_type == "alimtalk" else T.SUCCESS
                ctk.CTkLabel(row, text=msg_type, font=(T.get_font_family(), 10),
                             text_color=type_color, width=60).pack(side="left")

                status = item.get("status", "")
                status_color = T.SUCCESS if status == "queued" else T.ERROR
                ctk.CTkLabel(row, text=status, font=(T.get_font_family(), 10),
                             text_color=status_color, width=60).pack(side="left")

                ctk.CTkLabel(row, text=f"{item.get('cost', 0)}원",
                             font=(T.get_font_family(), 10),
                             text_color=T.TEXT_SECONDARY).pack(side="right", padx=8)

        except Exception as e:
            self.balance_label.configure(text="연결 오류")

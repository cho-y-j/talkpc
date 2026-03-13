"""사용량/잔액 페이지"""
import customtkinter as ctk
from ui.theme import AppTheme as T


class UsagePage(ctk.CTkFrame):
    """사용량 + 잔액 확인 페이지"""

    MSG_TYPE_LABEL = {
        "sms": "SMS",
        "lms": "LMS",
        "alimtalk": "알림톡",
    }

    MSG_TYPE_COLOR = {
        "sms": "#58a6ff",
        "lms": "#bc8cff",
        "alimtalk": "#3fb950",
    }

    STATUS_LABEL = {
        "queued": "발송대기",
        "success": "성공",
        "failed": "실패",
    }

    def __init__(self, parent, api_client=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color=T.BG_DARK)
        self.api_client = api_client
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 헤더
        header = ctk.CTkFrame(self, fg_color="transparent", height=40)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 8))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="사용량 / 잔액",
                     font=(T.get_font_family(), 16, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(side="left")
        ctk.CTkButton(header, text="새로고침", width=80, height=30,
                      font=(T.get_font_family(), 11),
                      fg_color=T.BG_HOVER, hover_color=T.BORDER,
                      text_color=T.TEXT_PRIMARY, corner_radius=6,
                      command=self.refresh).pack(side="right")

        # 메인 콘텐츠
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 16))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)  # 발송 이력이 공간 차지

        # ── 상단: 잔액 + 통계 (한 줄) ──
        top_frame = ctk.CTkFrame(content, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="stat")

        # 잔액
        self.balance_card = self._make_compact_card(top_frame, "잔액", "- 원", "#58a6ff")
        self.balance_card.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        # 오늘
        self.today_card = self._make_compact_card(top_frame, "오늘 발송", "- 건", "#3fb950")
        self.today_card.grid(row=0, column=1, padx=3, sticky="ew")

        # 이번 달
        self.month_card = self._make_compact_card(top_frame, "이번 달", "- 건", "#bc8cff")
        self.month_card.grid(row=0, column=2, padx=3, sticky="ew")

        # 전체
        self.total_card = self._make_compact_card(top_frame, "전체", "- 건", "#d29922")
        self.total_card.grid(row=0, column=3, padx=(6, 0), sticky="ew")

        # ── 하단: 발송 이력 (메인 영역) ──
        history_card = ctk.CTkFrame(content, fg_color=T.BG_CARD,
                                     corner_radius=10, border_width=1, border_color=T.BORDER)
        history_card.grid(row=1, column=0, sticky="nsew")
        history_card.grid_columnconfigure(0, weight=1)
        history_card.grid_rowconfigure(1, weight=1)

        # 이력 헤더
        history_header = ctk.CTkFrame(history_card, fg_color="transparent")
        history_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        ctk.CTkLabel(history_header, text="최근 발송 이력",
                     font=(T.get_font_family(), 13, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(side="left")

        # 테이블 헤더
        col_header = ctk.CTkFrame(history_card, fg_color="transparent", height=28)
        col_header.grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 0))
        col_header.pack_propagate(False)
        for text, w in [("시간", 130), ("받는사람", 90), ("발송방법", 70),
                        ("상태", 70), ("내용", 0), ("비용", 60)]:
            if w > 0:
                ctk.CTkLabel(col_header, text=text, font=(T.get_font_family(), 10),
                             text_color=T.TEXT_MUTED, width=w, anchor="w").pack(side="left")
            else:
                ctk.CTkLabel(col_header, text=text, font=(T.get_font_family(), 10),
                             text_color=T.TEXT_MUTED, anchor="w").pack(side="left", fill="x", expand=True)

        # 이력 리스트 (스크롤)
        self.history_scroll = ctk.CTkScrollableFrame(
            history_card, fg_color="transparent",
            scrollbar_button_color=T.BG_HOVER,
            scrollbar_button_hover_color=T.BORDER,
        )
        self.history_scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=(4, 12))
        history_card.grid_rowconfigure(2, weight=1)

    def _make_compact_card(self, parent, title: str, value: str, accent: str) -> ctk.CTkFrame:
        """컴팩트한 통계 카드"""
        card = ctk.CTkFrame(parent, fg_color=T.BG_CARD, corner_radius=10,
                            border_width=1, border_color=T.BORDER, height=75)
        card.pack_propagate(False)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text=title, font=(T.get_font_family(), 10),
                     text_color=T.TEXT_MUTED).pack(anchor="w", padx=14, pady=(10, 2))

        card.value_label = ctk.CTkLabel(card, text=value,
                                         font=(T.get_font_family(), 18, "bold"),
                                         text_color=accent)
        card.value_label.pack(anchor="w", padx=14)

        card.sub_label = ctk.CTkLabel(card, text="",
                                       font=(T.get_font_family(), 9),
                                       text_color=T.TEXT_MUTED)
        card.sub_label.pack(anchor="w", padx=14)

        return card

    def refresh(self):
        """서버에서 데이터 가져와 갱신"""
        if not self.api_client or not self.api_client.is_logged_in:
            return

        try:
            # 오늘 사용량 + 잔액
            daily = self.api_client.get_daily_usage()
            balance = daily.get("balance", 0)
            self.balance_card.value_label.configure(text=f"{balance:,}원")

            today_count = daily.get("count", 0)
            today_cost = daily.get("cost", 0)
            self.today_card.value_label.configure(text=f"{today_count:,}건")
            self.today_card.sub_label.configure(text=f"{today_cost:,}원")

            # 이번 달
            monthly = self.api_client.get_monthly_usage()
            month_count = monthly.get("count", 0)
            month_cost = monthly.get("cost", 0)
            self.month_card.value_label.configure(text=f"{month_count:,}건")
            self.month_card.sub_label.configure(text=f"{month_cost:,}원")

            # 전체 통계
            stats = self.api_client.get_usage_stats()
            total_count = stats.get("total_count", 0)
            total_cost = stats.get("total_cost", 0)
            self.total_card.value_label.configure(text=f"{total_count:,}건")
            self.total_card.sub_label.configure(text=f"{total_cost:,}원")

            # 최근 발송 이력
            history = self.api_client.get_send_history(page=1, size=50)
            for w in self.history_scroll.winfo_children():
                w.destroy()

            if not history:
                ctk.CTkLabel(self.history_scroll, text="발송 기록이 없습니다",
                             font=(T.get_font_family(), 12),
                             text_color=T.TEXT_MUTED).pack(pady=40)
                return

            for i, item in enumerate(history):
                bg = T.BG_INPUT if i % 2 == 0 else "transparent"
                row = ctk.CTkFrame(self.history_scroll, fg_color=bg,
                                   corner_radius=4, height=34)
                row.pack(fill="x", pady=1)
                row.pack_propagate(False)

                # 시간
                created = item.get("created_at", "")
                time_str = created[5:16].replace("T", " ") if len(created) >= 16 else created
                ctk.CTkLabel(row, text=time_str,
                             font=(T.get_font_family(), 10),
                             text_color=T.TEXT_SECONDARY, width=130, anchor="w"
                             ).pack(side="left", padx=(10, 0))

                # 받는사람
                ctk.CTkLabel(row, text=item.get("contact_name", "-"),
                             font=(T.get_font_family(), 11),
                             text_color=T.TEXT_PRIMARY, width=90, anchor="w"
                             ).pack(side="left")

                # 발송방법 (한글 표시)
                msg_type = item.get("msg_type", "")
                type_label = self.MSG_TYPE_LABEL.get(msg_type, msg_type)
                type_color = self.MSG_TYPE_COLOR.get(msg_type, T.TEXT_SECONDARY)
                ctk.CTkLabel(row, text=type_label,
                             font=(T.get_font_family(), 10, "bold"),
                             text_color=type_color, width=70, anchor="w"
                             ).pack(side="left")

                # 상태
                status = item.get("status", "")
                status_label = self.STATUS_LABEL.get(status, status)
                if status == "queued":
                    status_color = T.WARNING
                elif status == "success":
                    status_color = T.SUCCESS
                else:
                    status_color = T.ERROR
                ctk.CTkLabel(row, text=status_label,
                             font=(T.get_font_family(), 10),
                             text_color=status_color, width=70, anchor="w"
                             ).pack(side="left")

                # 메시지 미리보기
                preview = item.get("message_preview", "")
                if preview:
                    ctk.CTkLabel(row, text=preview[:30],
                                 font=(T.get_font_family(), 10),
                                 text_color=T.TEXT_MUTED, anchor="w"
                                 ).pack(side="left", fill="x", expand=True)
                else:
                    ctk.CTkFrame(row, fg_color="transparent").pack(side="left", fill="x", expand=True)

                # 비용
                cost = item.get("cost", 0)
                ctk.CTkLabel(row, text=f"{cost}원",
                             font=(T.get_font_family(), 10),
                             text_color=T.TEXT_SECONDARY, width=60, anchor="e"
                             ).pack(side="right", padx=(0, 10))

        except Exception as e:
            self.balance_card.value_label.configure(text="연결 오류")

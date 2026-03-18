"""브랜드톡 디자이너 페이지 - 플레이스홀더"""
import customtkinter as ctk
from ui.theme import AppTheme as T


class BrandtalkDesignerPage(ctk.CTkFrame):
    def __init__(self, parent, api_client=None, **kwargs):
        super().__init__(parent, fg_color=T.BG_DARK, **kwargs)
        self.api_client = api_client
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="🟡 브랜드톡 디자이너",
            font=(T.get_font_family(), 24, "bold"),
            text_color=T.TEXT_PRIMARY
        ).pack(pady=(40, 10))

        ctk.CTkLabel(
            self, text="브랜드톡 메시지를 디자인하고 미리보기할 수 있습니다.",
            font=(T.get_font_family(), 13),
            text_color=T.TEXT_SECONDARY
        ).pack(pady=(0, 20))

        info_card = ctk.CTkFrame(self, fg_color=T.BG_CARD, corner_radius=12)
        info_card.pack(padx=40, fill="x")

        ctk.CTkLabel(
            info_card, text="사용하려면 다음이 필요합니다:",
            font=(T.get_font_family(), 12, "bold"),
            text_color=T.TEXT_PRIMARY
        ).pack(padx=20, pady=(15, 5), anchor="w")

        for item in ["카카오톡 비즈니스 채널 개설", "senderKey 발급 (세종텔레콤)", "080 수신거부번호"]:
            ctk.CTkLabel(
                info_card, text=f"  • {item}",
                font=(T.get_font_family(), 11),
                text_color=T.TEXT_SECONDARY
            ).pack(padx=20, pady=1, anchor="w")

        ctk.CTkLabel(info_card, text="", height=15).pack()

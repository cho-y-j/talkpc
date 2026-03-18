"""API 클라이언트 - SaaS 서버와 통신"""
import requests
from typing import Optional


class APIClient:
    """TalkPC SaaS API 클라이언트"""

    # 프로그램 내장 API 키 - 이 키 없으면 서버 접근 불가
    _API_KEY = "tpc-k8x2m9vQfR7wLpN3jY6sT0dA4hE1cU5b"

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url.rstrip("/")
        self.token: Optional[str] = None
        self.user_info: dict = {}

    @property
    def is_logged_in(self) -> bool:
        return self.token is not None

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/json",
            "X-API-Key": self._API_KEY,
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _url(self, path: str) -> str:
        return f"{self.server_url}/api{path}"

    def _get(self, path: str, params: dict = None) -> dict:
        r = requests.get(self._url(path), headers=self._headers(), params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict = None) -> dict:
        r = requests.post(self._url(path), headers=self._headers(), json=data, timeout=10)
        r.raise_for_status()
        return r.json()

    def _put(self, path: str, data: dict = None) -> dict:
        r = requests.put(self._url(path), headers=self._headers(), json=data, timeout=10)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str) -> dict:
        r = requests.delete(self._url(path), headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.json()

    # === 인증 ===

    def register(self, username: str, password: str, name: str,
                 phone: str = "", email: str = "") -> dict:
        data = {"username": username, "password": password, "name": name,
                "phone": phone, "email": email}
        result = self._post("/auth/register", data)
        self.token = result["access_token"]
        self.user_info = {
            "user_id": result["user_id"], "username": result["username"],
            "name": result["name"], "role": result["role"]
        }
        return result

    def login(self, username: str, password: str) -> dict:
        result = self._post("/auth/login", {"username": username, "password": password})
        self.token = result["access_token"]
        self.user_info = {
            "user_id": result["user_id"], "username": result["username"],
            "name": result["name"], "role": result["role"]
        }
        return result

    def logout(self):
        self.token = None
        self.user_info = {}

    def change_password(self, old_password: str, new_password: str) -> dict:
        return self._post("/auth/change-password",
                          {"old_password": old_password, "new_password": new_password})

    # === 계정 ===

    def get_me(self) -> dict:
        return self._get("/account/me")

    def update_me(self, **kwargs) -> dict:
        return self._put("/account/me", kwargs)

    def get_balance(self) -> int:
        return self._get("/account/balance").get("balance", 0)

    # === 연락처 ===

    def get_contacts(self, category: str = None, search: str = None) -> list:
        params = {}
        if category:
            params["category"] = category
        if search:
            params["search"] = search
        return self._get("/contacts", params)

    def create_contact(self, data: dict) -> dict:
        return self._post("/contacts", data)

    def update_contact(self, contact_id: int, data: dict) -> dict:
        return self._put(f"/contacts/{contact_id}", data)

    def delete_contact(self, contact_id: int) -> dict:
        return self._delete(f"/contacts/{contact_id}")

    def import_contacts(self, filepath: str) -> dict:
        """엑셀 파일 업로드로 연락처 일괄 등록"""
        url = self._url("/contacts/import")
        headers = {"X-API-Key": self._API_KEY}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        with open(filepath, "rb") as f:
            r = requests.post(url, headers=headers, files={"file": f}, timeout=30)
        r.raise_for_status()
        return r.json()

    def export_contacts(self, filepath: str) -> str:
        """연락처 엑셀 다운로드"""
        url = self._url("/contacts/export")
        headers = {"X-API-Key": self._API_KEY}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(r.content)
        return filepath

    # === 템플릿 ===

    def get_templates(self, category: str = None) -> list:
        params = {"category": category} if category else {}
        return self._get("/templates", params)

    def create_template(self, data: dict) -> dict:
        return self._post("/templates", data)

    def update_template(self, template_id: int, data: dict) -> dict:
        return self._put(f"/templates/{template_id}", data)

    def delete_template(self, template_id: int) -> dict:
        return self._delete(f"/templates/{template_id}")

    # === 발송 ===

    def send_sms(self, contact_ids: list, message: str, subject: str = "") -> dict:
        data = {"contact_ids": contact_ids, "message": message}
        if subject:
            data["subject"] = subject
        return self._post("/send/sms", data)

    def send_alimtalk(self, contact_ids: list, message: str,
                      template_code: str = "", buttons: list = None,
                      fallback_type: str = "sms") -> dict:
        data = {"contact_ids": contact_ids, "message": message,
                "template_code": template_code, "fallback_type": fallback_type}
        if buttons:
            data["buttons"] = buttons
        return self._post("/send/alimtalk", data)

    def send_brandtalk(self, contact_ids: list, message: str,
                       bubble_type: str = "TEXT", targeting: str = "I",
                       buttons: list = None, image_url: str = "") -> dict:
        data = {"contact_ids": contact_ids, "message": message,
                "bubble_type": bubble_type, "targeting": targeting}
        if buttons:
            data["buttons"] = buttons
        if image_url:
            data["image_url"] = image_url
        return self._post("/send/brandtalk", data)

    def send_rcs(self, contact_ids: list, message: str,
                 msg_type: str = "standalone", title: str = "",
                 image_url: str = "", buttons: list = None,
                 cards: list = None, fallback_type: str = "sms") -> dict:
        data = {"contact_ids": contact_ids, "message": message,
                "msg_type": msg_type, "fallback_type": fallback_type}
        if title:
            data["title"] = title
        if image_url:
            data["image_url"] = image_url
        if buttons:
            data["buttons"] = buttons
        if cards:
            data["cards"] = cards
        return self._post("/send/rcs", data)

    def get_send_result(self, mseq: int) -> dict:
        return self._get(f"/send/result/{mseq}")

    def get_send_history(self, page: int = 1, size: int = 50) -> list:
        return self._get("/send/history", {"page": page, "size": size})

    # === 사용량 ===

    def get_daily_usage(self) -> dict:
        return self._get("/usage/daily")

    def get_monthly_usage(self) -> dict:
        return self._get("/usage/monthly")

    def get_usage_stats(self) -> dict:
        return self._get("/usage/stats")

    # === 크레딧 ===

    def get_credit_history(self) -> list:
        return self._get("/account/credits")

    def create_charge_request(self, amount: int, method: str = "bank") -> dict:
        return self._post("/account/charge-request", {"amount": amount, "method": method})

    def get_charge_requests(self) -> list:
        return self._get("/account/charge-requests")

    def get_pricing(self) -> dict:
        return self._get("/account/pricing")

from typing import Protocol

import httpx

from recruitment.config import Settings


class TelegramClient(Protocol):
    def send_message(self, *, chat_id: str, text: str) -> str: ...


class TelegramConfigurationError(RuntimeError):
    pass


class TelegramBotClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.telegram_bot_token:
            raise TelegramConfigurationError("TELEGRAM_BOT_TOKEN is not configured")
        self.bot_token = settings.telegram_bot_token

    def send_message(self, *, chat_id: str, text: str) -> str:
        response = httpx.post(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        try:
            payload = response.json()
        except ValueError as error:
            raise RuntimeError("Telegram API returned invalid JSON") from error
        if response.is_error or not payload.get("ok"):
            detail = payload.get("description") or response.text
            raise RuntimeError(
                f"Telegram API request failed ({response.status_code}): {detail}"
            )
        try:
            return str(payload["result"]["message_id"])
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError("Telegram API response did not include a message ID") from error

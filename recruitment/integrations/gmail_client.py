import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from recruitment.config import get_settings


@dataclass(frozen=True)
class GmailAttachment:
    filename: str
    attachment_id: str
    content: bytes | None = None


@dataclass(frozen=True)
class GmailMessage:
    id: str
    subject: str
    body: str
    attachments: list[GmailAttachment]


class GmailClient:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gmail_enabled:
            raise RuntimeError("GMAIL_ENABLED is false")
        if not _configured_path(settings.gmail_client_secret_file) or not _configured_path(
            settings.gmail_token_file
        ):
            raise RuntimeError("Gmail OAuth files are not configured")
        self.service = _build_service(
            settings.gmail_client_secret_file, settings.gmail_token_file
        )

    def list_messages_by_label(self, label_name: str, lookback_days: int) -> list[GmailMessage]:
        return self.list_messages_by_labels([label_name], lookback_days)

    def list_all_messages_by_label(self, label_name: str) -> list[GmailMessage]:
        """List every message in a label, across all Gmail result pages."""
        return self.list_messages_by_labels([label_name], lookback_days=None)

    def list_messages_by_labels(
        self, label_names: list[str], lookback_days: int | None
    ) -> list[GmailMessage]:
        query = f"newer_than:{max(lookback_days, 1)}d" if lookback_days else None
        message_refs_by_id: dict[str, dict] = {}
        for label_id in self.label_ids_for_names(label_names):
            for item in self._list_message_refs(label_id, query):
                message_refs_by_id[item["id"]] = item
        message_refs = list(message_refs_by_id.values())
        return [self.get_message(item["id"]) for item in message_refs]

    def label_ids_for_names(self, label_names: list[str]) -> list[str]:
        settings = get_settings()
        requested = {normalize_label_name(label_name) for label_name in label_names}
        label_ids: list[str] = []
        for label in self.labels():
            label_name = str(label.get("name") or "")
            normalized = normalize_label_name(label_name)
            parent = normalized.split("/", 1)[0]
            if normalized in requested or (
                settings.gmail_include_child_labels and parent in requested
            ):
                label_ids.append(str(label["id"]))
        if not label_ids:
            raise RuntimeError(f"Gmail label was not found: {', '.join(label_names)}")
        return label_ids

    def labels(self) -> list[dict]:
        return self.service.users().labels().list(userId="me").execute().get("labels", [])

    def label_names(self) -> list[str]:
        return sorted(str(label.get("name") or "") for label in self.labels())

    def _list_message_refs(self, label_id: str, query: str | None) -> list[dict]:
        refs: list[dict] = []
        page_token = None
        while True:
            request_args: dict[str, Any] = {
                "userId": "me",
                "labelIds": [label_id],
                "pageToken": page_token,
                "maxResults": 100,
            }
            if query:
                request_args["q"] = query
            request = self.service.users().messages().list(**request_args)
            response = request.execute()
            refs.extend(response.get("messages", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                return refs

    def get_message(self, message_id: str) -> GmailMessage:
        raw = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        headers = {
            header["name"].lower(): header["value"]
            for header in raw["payload"].get("headers", [])
        }
        subject = headers.get("subject", "")
        body = _body_from_payload(raw.get("payload", {}))
        attachments = self._attachments_from_payload(raw.get("payload", {}))
        return GmailMessage(id=message_id, subject=subject, body=body, attachments=attachments)

    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        response = (
            self.service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )
        return _decode_base64url(response.get("data", ""))

    def _label_id(self, label_name: str) -> str:
        for label in self.labels():
            if normalize_label_name(str(label.get("name") or "")) == normalize_label_name(
                label_name
            ):
                return str(label["id"])
        raise RuntimeError(f"Gmail label was not found: {label_name}")

    def _attachments_from_payload(self, payload: dict[str, Any]) -> list[GmailAttachment]:
        attachments: list[GmailAttachment] = []
        for part in _walk_parts(payload):
            filename = part.get("filename") or ""
            body = part.get("body") or {}
            attachment_id = body.get("attachmentId")
            if not filename or not attachment_id:
                continue
            attachments.append(
                GmailAttachment(
                    filename=filename,
                    attachment_id=attachment_id,
                )
            )
        return attachments


def _build_service(client_secret_file: Path, token_file: Path):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as error:
        raise RuntimeError("Install Gmail API dependencies from requirements.txt") from error

    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    credentials = None
    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(token_file), scopes)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except Exception:
                credentials = None
        if not credentials or not credentials.valid:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), scopes)
            credentials = flow.run_local_server(port=0)
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(credentials.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=credentials)


def _configured_path(path: Path | None) -> bool:
    return path is not None and str(path).strip() not in {"", "."}


def normalize_label_name(value: str) -> str:
    return " ".join(value.strip().split())


def _walk_parts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    parts = [payload]
    for part in payload.get("parts", []) or []:
        parts.extend(_walk_parts(part))
    return parts


def _body_from_payload(payload: dict[str, Any]) -> str:
    chunks: list[str] = []
    for part in _walk_parts(payload):
        mime_type = part.get("mimeType", "")
        body = part.get("body") or {}
        data = body.get("data")
        if data and mime_type in {"text/plain", "text/html"}:
            chunks.append(_decode_base64url(data).decode("utf-8", errors="ignore"))
    return "\n\n".join(chunks)


def _decode_base64url(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)

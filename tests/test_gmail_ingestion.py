from types import SimpleNamespace

from sqlmodel import SQLModel, Session, create_engine

from recruitment.integrations.gmail_client import GmailAttachment, GmailClient, GmailMessage
from recruitment.services import email_ingestion


class FakeGmailClient:
    def __init__(self, messages: list[GmailMessage]) -> None:
        self.messages = messages
        self.all_messages_calls = 0
        self.cv_label_requests: list[list[str]] = []
        self.downloaded_attachment_ids: list[str] = []

    def label_names(self) -> list[str]:
        return ["CVs", "Jobs"]

    def list_messages_by_label(self, _: str, __: int) -> list[GmailMessage]:
        return []

    def list_all_messages_by_label(self, _: str) -> list[GmailMessage]:
        self.all_messages_calls += 1
        return self.messages

    def list_all_messages_by_labels(self, labels: list[str]) -> list[GmailMessage]:
        self.all_messages_calls += 1
        self.cv_label_requests.append(labels)
        return self.messages

    def download_attachment(self, _: str, attachment_id: str) -> bytes:
        self.downloaded_attachment_ids.append(attachment_id)
        return attachment_id.encode()


def test_gmail_cv_sync_retries_only_failed_attachments(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    message = GmailMessage(
        id="message-1",
        subject="CVs",
        body="",
        attachments=[
            GmailAttachment(filename="first.txt", attachment_id="attachment-1"),
            GmailAttachment(filename="second.txt", attachment_id="attachment-2"),
        ],
    )
    client = FakeGmailClient([message])
    settings = SimpleNamespace(
        gmail_enabled=True,
        gmail_jobs_label="Jobs",
        gmail_cvs_label="CVs",
        gmail_lookback_days=1,
    )
    attempts: list[str] = []

    def fake_ingest_cv_file(*, original_filename: str, **_: object) -> tuple[str, str]:
        attempts.append(original_filename)
        if original_filename == "second.txt" and attempts.count(original_filename) == 1:
            raise ValueError("temporary parsing failure")
        return "cand_1", f"cvfile_{len(attempts)}"

    monkeypatch.setattr(email_ingestion, "get_settings", lambda: settings)
    monkeypatch.setattr(email_ingestion, "GmailClient", lambda: client)
    monkeypatch.setattr(email_ingestion, "ingest_cv_file", fake_ingest_cv_file)

    with Session(engine) as session:
        first_run = email_ingestion.ingest_gmail_daily(session)
        session.commit()
        client.messages = [
            GmailMessage(
                id="message-1",
                subject="CVs",
                body="",
                attachments=[
                    GmailAttachment(filename="first.txt", attachment_id="new-attachment-1"),
                    GmailAttachment(filename="second.txt", attachment_id="new-attachment-2"),
                ],
            )
        ]
        second_run = email_ingestion.ingest_gmail_daily(session)

    assert first_run["cvs_ingested"] == 1
    assert len(first_run["errors"]) == 1
    assert second_run["cvs_ingested"] == 1
    assert client.all_messages_calls == 2
    assert client.cv_label_requests == [["CVs", "INBOX"], ["CVs", "INBOX"]]
    assert client.downloaded_attachment_ids == ["attachment-1", "attachment-2", "new-attachment-2"]


def test_gmail_client_lists_all_pages_without_a_date_query() -> None:
    class FakeRequest:
        def __init__(self, response: dict) -> None:
            self.response = response

        def execute(self) -> dict:
            return self.response

    class FakeMessages:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def list(self, **kwargs: object) -> FakeRequest:
            self.calls.append(kwargs)
            if kwargs.get("pageToken") is None:
                return FakeRequest({"messages": [{"id": "one"}], "nextPageToken": "next"})
            return FakeRequest({"messages": [{"id": "two"}]})

    class FakeUsers:
        def __init__(self, messages: FakeMessages) -> None:
            self.messages_client = messages

        def messages(self) -> FakeMessages:
            return self.messages_client

    class FakeService:
        def __init__(self, messages: FakeMessages) -> None:
            self.users_client = FakeUsers(messages)

        def users(self) -> FakeUsers:
            return self.users_client

    messages = FakeMessages()
    client = object.__new__(GmailClient)
    client.service = FakeService(messages)

    assert client._list_message_refs("label-1", query=None) == [{"id": "one"}, {"id": "two"}]
    assert all("q" not in call for call in messages.calls)


def test_gmail_cv_listing_filters_for_attachments(monkeypatch) -> None:
    client = object.__new__(GmailClient)
    captured: dict[str, object] = {}

    def list_refs(_: str, query: str | None) -> list[dict]:
        captured["query"] = query
        return []

    monkeypatch.setattr(client, "label_ids_for_names", lambda _: ["label-1"])
    monkeypatch.setattr(client, "_list_message_refs", list_refs)
    monkeypatch.setattr(client, "get_message", lambda _: None)

    assert client.list_all_messages_by_label("CVs") == []
    assert captured["query"] == "has:attachment"

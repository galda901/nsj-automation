from recruitment.database import get_session
from recruitment.services.email_ingestion import ingest_gmail_daily


def main() -> None:
    session = next(get_session())
    result = ingest_gmail_daily(session)
    session.commit()
    print(result)


if __name__ == "__main__":
    main()

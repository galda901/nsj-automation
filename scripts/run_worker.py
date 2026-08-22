import argparse
import json

from sqlmodel import Session, select

from recruitment.config import get_settings
from recruitment.database import create_db_and_tables
from recruitment.database import engine
from recruitment.models.notification import NotificationOutbox
from recruitment.services.background_worker import WorkerLockUnavailable, worker_loop


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Gmail matching and Telegram worker")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument(
        "--json", action="store_true", help="Print the full diagnostic JSON summary"
    )
    args = parser.parse_args()

    create_db_and_tables()
    try:
        for result in worker_loop(once=args.once):
            if args.json:
                print(json.dumps(result, ensure_ascii=False, default=str))
            else:
                print_readable_summary(result)
    except WorkerLockUnavailable as error:
        print(str(error))


def print_readable_summary(result: dict) -> None:
    settings = get_settings()
    errors = result.get("errors", [])
    print(f"Worker: {'ERROR' if errors else 'OK'}")
    ingestion = result.get("ingestion", {})
    print(
        "Gmail: "
        f"{ingestion.get('jobs_drafted', 0)} new job(s), "
        f"{ingestion.get('cvs_ingested', 0)} new/updated candidate(s), "
        f"{ingestion.get('duplicates_skipped', 0)} duplicate(s) skipped"
    )
    print(
        "Matching: "
        f"{result.get('jobs_matched', 0)} job(s), "
        f"{result.get('matches_evaluated', 0)} comparison(s)"
    )
    delivery = result.get("delivery", {})
    if settings.telegram_dry_run or not settings.telegram_enabled:
        print(
            "Telegram: DRY RUN / disabled — "
            f"{result.get('notifications_created', 0)} new qualifying notification(s); "
            "nothing was sent"
        )
    else:
        print(
            "Telegram: "
            f"{delivery.get('sent', 0)} sent, {delivery.get('failed', 0)} failed"
        )

    with Session(engine) as session:
        notifications = list(
            session.exec(
                select(NotificationOutbox)
                .where(NotificationOutbox.status.in_(["pending", "failed", "sending"]))
                .order_by(NotificationOutbox.created_at.desc())
                .limit(20)
            ).all()
        )
    if not notifications:
        print("Telegram messages: none pending.")
    else:
        print(f"Telegram messages ({len(notifications)} pending/retry):")
        for notification in notifications:
            print(
                f"- [{notification.status.upper()}] "
                f"{notification.candidate_name} → {notification.job_title} "
                f"({notification.score:.1f}/100)"
            )
            print(notification.message_body)
    if errors:
        print("Errors:")
        for error in errors:
            print(f"- {error}")


if __name__ == "__main__":
    main()

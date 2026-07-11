from sqlmodel import Session

from recruitment.database import engine
from recruitment.services.excel_exporter import export_candidates_to_excel


def main() -> None:
    with Session(engine) as session:
        path = export_candidates_to_excel(session)
    print(f"Exported candidates to: {path}")


if __name__ == "__main__":
    main()

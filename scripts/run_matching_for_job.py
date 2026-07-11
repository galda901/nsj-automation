import argparse

from sqlmodel import Session

from recruitment.database import engine
from recruitment.services.matching_engine import match_candidates_for_job


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("job_id")
    args = parser.parse_args()
    with Session(engine) as session:
        results = match_candidates_for_job(args.job_id, session)
    for result in results:
        print(f"{result.candidate_id}: {result.total_score:.1f}")


if __name__ == "__main__":
    main()

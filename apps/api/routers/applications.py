from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from recruitment.database import get_session
from recruitment.models.application import Application

router = APIRouter()


@router.get("", response_model=list[Application])
def list_applications(session: Session = Depends(get_session)) -> list[Application]:
    return list(session.exec(select(Application).order_by(Application.received_at.desc())).all())

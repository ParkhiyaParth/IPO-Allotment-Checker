from fastapi import APIRouter

from app.models.schemas import RegisterPushTokenRequest
from app.services import push_token_repository

router = APIRouter(prefix="/push-tokens", tags=["push"])


@router.post("", status_code=204)
async def register_push_token(body: RegisterPushTokenRequest) -> None:
    push_token_repository.register(body.token, body.device_id)

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ResetPasswordMessage(BaseModel):
    id: UUID
    user_id: str = Field(..., alias="userId")
    email_address: EmailStr = Field(..., alias="emailAddress")
    subject: str
    body: str
    published_at: datetime = Field(..., alias="publishedAt")
    sent_at: datetime | None = None

    # Turn on snake_case and camelCase for import data
    model_config = {
        "populate_by_name": True
    }





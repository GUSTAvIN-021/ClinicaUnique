from pydantic import BaseModel, Field, field_validator
from app.models.entities import Role


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    totp_code: str | None = Field(default=None, min_length=6, max_length=8)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        local, separator, domain = normalized.partition("@")
        if not separator or not local or not domain or "@" in domain or any(char.isspace() for char in normalized):
            raise ValueError("Informe um e-mail válido.")
        return normalized


class ChangePasswordRequest(BaseModel):
    current_password: str | None = Field(default=None, min_length=8, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class CurrentPasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)


class TotpCodeRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=8)


class UserOut(BaseModel):
    id: int
    email: str
    role: Role
    active: bool
    professional_id: int | None
    mfa_enabled: bool = False

    class Config:
        from_attributes = True

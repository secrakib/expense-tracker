from pydantic import BaseModel,model_validator
from typing import Annotated, Optional
from datetime import date

# ── Pydantic Models ──────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class AddExpenseRequest(BaseModel):
    category: str
    expense: float
    date: date  # YYYY-MM-DD


class UpdateExpenseRequest(BaseModel):
    id: int
    category: Optional[str] = None
    expense: Optional[float] = None
    date: Optional[str] = None

class DeleteExpenseRequest(BaseModel):
    category: Optional[str] = None
    date: Optional[str] = None
    min_expense: Optional[float] = None
    max_expense: Optional[float] = None

    @model_validator(mode="after")
    def at_least_one_filter(self):
        filters = [
            self.category,
            self.date,
            self.min_expense,
            self.max_expense,
        ]
        if not any(f is not None and str(f).strip() != "" for f in filters):
            raise ValueError("At least one filter required")
        return self
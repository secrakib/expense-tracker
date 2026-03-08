from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, status,Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel,model_validator
from datetime import date

from backend.src.credentials.add_values import add_values as db_register
from backend.src.credentials.create_table import create_table as create_credentials_table
from backend.src.feature.create_table import create_table as create_expenses_table
from backend.src.feature.add_values import add_values as db_add_expense
from backend.src.feature.delete_record import delete_record as db_delete
from backend.src.feature.update_values import update_values as db_update
from backend.src.feature.filter_and_show import filter_expenses as db_filter
from backend.src.feature.initial import initial
from backend.src.credentials.delete_user import delete_user
from backend.database.globals import location

# ── Config ──────────────────────────────────────────────────────────────────
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"


password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="Expense Tracker API")

# ── DB init ──────────────────────────────────────────────────────────────────
create_credentials_table(location)
create_expenses_table(location)

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

# ── Helpers ──────────────────────────────────────────────────────────────────
def get_hashed_password_from_db(username: str) -> Optional[str]:
    conn, cursor = initial(location)
    cursor.execute("SELECT password FROM credentials WHERE user_name = ?", (username.lower(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        password = row[0]
    else:
        password = None
    return password

def create_access_token(username: str, ACCESS_TOKEN_EXPIRE_MINUTES:int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# ── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/register", status_code=201)
def register(body: RegisterRequest):
    """Register a new user with an encrypted password."""
    hashed = password_hash.hash(body.password)
    result = db_register(body.username, hashed, location)
    if result is None:
        return {"message": f"User '{body.username.lower()}' registered successfully."}
    raise HTTPException(status_code=400, detail="Username already exists.")


@app.post("/token", response_model=Token)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
          ACCESS_TOKEN_EXPIRE_MINUTES:Annotated[int,Query(gt=0)] = 30):
    """Login and receive a JWT access token."""
    hashed = get_hashed_password_from_db(form_data.username)
    if not hashed:
        password_hash.verify(form_data.password, DUMMY_HASH)  # timing-safe
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    if not password_hash.verify(form_data.password, hashed):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    return Token(access_token=create_access_token(form_data.username.lower(),ACCESS_TOKEN_EXPIRE_MINUTES), token_type="bearer")


@app.post("/expenses", status_code=201)
def add_expense(
    body: AddExpenseRequest,
    username: Annotated[str, Depends(get_current_user)]
):
    """Add an expense. Username comes from JWT."""
    db_add_expense(username, body.category, body.expense, body.date, location)
    return {"message": "Expense added successfully."}


@app.get("/expenses")
def read_expenses(
    username: Annotated[str, Depends(get_current_user)], 
    category: Optional[str] = None,
    date: Optional[str] = None,
    min_expense: Optional[float] = None,
    max_expense: Optional[float] = None
):
    """Read/filter expenses. Username comes from JWT."""
    rows = db_filter(location, username, category, date, min_expense, max_expense)
    keys = ["id", "user_name", "category", "expense", "date"]
    results = []
    for r in rows:
        row_dict = dict(zip(keys, r))
        results.append(row_dict)
    return {"expenses": results}


@app.put("/expenses")
def update_expense(
    body: UpdateExpenseRequest,
    username: Annotated[str, Depends(get_current_user)]
):
    """Update an expense by ID. Username comes from JWT."""
    try:
        db_update(location, body.id, username, body.category, body.expense, body.date)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": f"Expense {body.id} updated successfully."}


@app.delete("/expenses")
def delete_expense(
    body: DeleteExpenseRequest,
    username: Annotated[str, Depends(get_current_user)]
):
    """Delete expenses by filter. Username comes from JWT."""
    result = db_delete(location, username, body.category, body.date, body.min_expense, body.max_expense)
    return result


@app.delete("/expenses/{username}", status_code=200)
def delete_user(
    username: str,
    current_user: Annotated[str, Depends(get_current_user)]
):
    """Delete a user by username. Only the user themselves can delete their account."""
    if current_user != username.lower():
        raise HTTPException(status_code=403, detail="Not a user.")
    try:
        result = delete_user(location, username.lower())
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

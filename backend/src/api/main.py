from typing import Annotated, Optional
from fastapi import Depends, FastAPI, HTTPException, status,Query, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash



from backend.src.credentials.add_values import add_values as db_register
from backend.src.credentials.create_table import create_table as create_credentials_table
from backend.src.feature.create_table import create_table as create_expenses_table
from backend.src.feature.add_values import add_values as db_add_expense
from backend.src.feature.delete_record import delete_record as db_delete
from backend.src.feature.update_values import update_values as db_update
from backend.src.feature.filter_and_show import filter_expenses as db_filter
from backend.src.feature.initial import initial
from backend.src.credentials.delete_user import delete_user as db_delete_user
from backend.database.globals import location
from backend.src.api.models.models import Token,RegisterRequest,AddExpenseRequest,UpdateExpenseRequest,DeleteExpenseRequest
from backend.src.api.helpers.helpers import get_current_user,get_hashed_password_from_db,create_access_token


password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI(title="Expense Tracker API")

# ── DB init ──────────────────────────────────────────────────────────────────
create_credentials_table(location)
create_expenses_table(location)


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/register", status_code=201)
def register(body: RegisterRequest)->dict:
    """Register a new user with an encrypted password."""
    hashed = password_hash.hash(body.password)
    result = db_register(body.username, hashed, location)
    if result is None:
        return {"message": f"User '{body.username.lower()}' registered successfully."}
    raise HTTPException(status_code=400, detail="Username already exists.")


@app.post("/token")
def login(response: Response,
          form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
          ACCESS_TOKEN_EXPIRE_MINUTES:Annotated[int,Query(gt=0)] = 30)-> dict:
    """Login and receive a JWT access token."""
    hashed = get_hashed_password_from_db(form_data.username)
    if not hashed:
        password_hash.verify(form_data.password, DUMMY_HASH)  # timing-safe
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    if not password_hash.verify(form_data.password, hashed):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    #return Token(access_token=create_access_token(form_data.username.lower(),ACCESS_TOKEN_EXPIRE_MINUTES), token_type="bearer")
    token = create_access_token(form_data.username.lower(), ACCESS_TOKEN_EXPIRE_MINUTES)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,       # JS cannot read it
        secure=True,         # HTTPS only (disable in dev if needed)
        samesite="lax"       # CSRF protection
    )
    
    return {"message": "Login successful"}


@app.post("/expenses", status_code=201)
def add_expense(
    body: AddExpenseRequest,
    username: Annotated[str, Depends(get_current_user)]
)-> dict:
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
)-> dict:
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
)-> dict:
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
)->dict:
    """Delete expenses by filter. Username comes from JWT."""
    result = db_delete(location, username, body.category, body.date, body.min_expense, body.max_expense)
    return result


@app.delete("/expenses/{username}", status_code=200)
def delete_user(
    user_name: Annotated[str, Depends(get_current_user)]
)->dict:
    """Delete a user by username"""
    try:
        result = db_delete_user(location, user_name.lower())
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

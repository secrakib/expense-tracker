from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from fastapi import  HTTPException,Cookie
import jwt
from jwt.exceptions import InvalidTokenError
from backend.database.globals import location
from backend.src.feature.initial import initial
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"


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

'''async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")'''

async def get_current_user(access_token: Annotated[str | None, Cookie()] = None) -> str:
    if access_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
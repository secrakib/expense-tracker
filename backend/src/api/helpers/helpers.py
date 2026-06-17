# File: backend/src/api/helpers/helpers.py
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from dotenv import load_dotenv
import jwt,os
from fastapi import Depends,HTTPException, Cookie, Header
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from backend.database.globals import DATABASE_URL
from backend.src.feature.initial import initial
load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
print(SECRET_KEY)
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") 

def get_hashed_password_from_db(username: str) -> Optional[str]:
    conn, cursor = initial(DATABASE_URL)
    cursor.execute(
        "SELECT password FROM credentials WHERE user_name = %s",
        (username.lower(),),
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def create_access_token(username: str, ACCESS_TOKEN_EXPIRE_MINUTES: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
# expense-tracker

## Environment Variables

Before running the project, create a `.env` file in the project root and add the following variables:
### Backend
```env
DATABASE_URL= str | "FROM SUPABASE"
SECRET_KEY= your-64-character-random-secret-key-here (64-character random secret key used for JWT signing (HS256))
```
### Frontend
``` env
BACKEND_URL = str | "Url of the backend"
```
These environment variables are required for the application to run correctly.

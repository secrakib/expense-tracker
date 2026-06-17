# expense-tracker

## Environment Variables

Before running the project, create a `.env` file in the project root and add the following variables:

```env
DATABASE_URL= FROM SUPABASE
BACKEND_URL= BACKEND URL TO CONNECT THE FRONT TO THE BACK
SECRET_KEY= your-64-character-random-secret-key-here (64-character random secret key used for JWT signing (HS256))
```

These environment variables are required for the application to run correctly.
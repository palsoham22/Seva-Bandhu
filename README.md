# Seva Bandhu

Seva Bandhu is a Django-based service-request platform with separate customer and technician workflows. It supports account registration, service requests, job updates, request tracking, payments, invoices, notifications, and technician location updates.

## Technology

- Backend: Python, Django, Django Channels
- Current frontend: Django templates, HTML, CSS, and JavaScript
- Database: SQLite for local development (kept out of version control)

## Project structure

```text
SevaBandhu/
├── backend/                 # Django application and Django-template UI
├── SevaBandhu-Frontend/     # Reserved for a future standalone frontend
├── .env.example             # Safe configuration template
├── .gitignore
└── README.md
```

## Local setup

1. Create and activate a Python virtual environment.
2. Install backend dependencies:

   ```powershell
   cd backend
   python -m pip install -r requirements.txt
   ```

3. Create local configuration from `.env.example` at the repository root and replace every placeholder with your own values. Never commit `.env`.
4. Apply migrations (a local database is created if one is not already present):

   ```powershell
   python manage.py migrate
   ```

5. Start the backend:

   ```powershell
   python manage.py runserver
   ```

   Then open `http://127.0.0.1:8000/`.

## Frontend

There is no standalone frontend yet. The working UI is served by Django from `backend/core/templates/`. When a standalone frontend is created, keep its source and package manifest in `SevaBandhu-Frontend/` and integrate it without removing the Django templates until the replacement has been tested.

## Security notes

- Keep `.env`, SQLite databases, uploaded media, virtual environments, and build artifacts out of Git.
- Use a unique `DJANGO_SECRET_KEY` and separate SMTP credentials per environment.
- Rotate any credentials that were previously committed or shared.
- Do not commit customer, technician, or other local application data.

## Future improvements

- Add a tested standalone frontend when the product is ready for it.
- Add automated tests and continuous integration.
- Configure production-specific settings, static-file hosting, and a managed database.

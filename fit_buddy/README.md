# FitBuddy

FitBuddy is a full-stack fitness and nutrition planning example built from the supplied project reference. Django owns accounts, HTML pages, validation, database records, and the admin site. A separate FastAPI service owns AI generation and calls Gemini when configured. Browser code talks only to Django; the Gemini key never reaches the browser.

The app is usable without a Gemini key: FastAPI supplies a conservative local plan and tips until a key is configured. AI output is general wellness guidance, not medical diagnosis or treatment.

## Requirements

- Python 3.12 or newer
- A terminal with access to this project folder
- Optional: a Google Gemini API key
- Optional for production: PostgreSQL or MySQL server

## First-time setup (Windows PowerShell)

Run these commands from the project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set a long, private `DJANGO_SECRET_KEY` and `AI_SERVICE_TOKEN`. The example token is for local development only; use the same newly generated secret in both services for deployment. Add `GEMINI_API_KEY` to enable Gemini generation; leave it blank to use the local fallback. Keep `.env` out of source control.

Create the development database and an administrator account:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

The initial migration is included in `plans/migrations/0001_initial.py`. After changing models, create and apply a migration:

```powershell
python manage.py makemigrations
python manage.py migrate
```

## Run both services

Open two PowerShell terminals in the project root, and activate `.venv` in each.

Terminal 1, AI service:

```powershell
python -m uvicorn fastapi_service.main:app --reload --port 8001
```

Terminal 2, Django web app:

```powershell
python manage.py runserver 8000
```

Visit `http://127.0.0.1:8000/`. Create an account, complete your profile, and generate a plan. The staff dashboard is at `/admin/`; Django's model management is at `/django-admin/`. FastAPI health is `/health/` and its interactive API documentation is `/docs` on port 8001.

## Project map

- `config/settings.py` — Django configuration, SQLite/PostgreSQL connection settings, static files, and service URL.
- `config/urls.py` — HTML routes, Django admin, and JSON API routes.
- `plans/models.py` — user profiles, workout plans/days, nutrition plans/meals, feedback, progress, and tips.
- `plans/forms.py` — server-side input bounds and allowed values.
- `plans/views.py` — session authentication, ownership checks, page rendering, and REST endpoints.
- `plans/services.py` — private server-to-server calls to FastAPI and normalized plan persistence.
- `plans/admin.py` — searchable Django admin views for stored FitBuddy records.
- `plans/migrations/` — schema history applied by `manage.py migrate`.
- `templates/` — requested pages: `index.html`, `profile.html`, `result.html`, `plan.html`, `nutrition.html`, `tips.html`, `feedback.html`, `dashboard.html`, `login.html`, `register.html`, and `admin.html`, plus shared `base.html`.
- `static/css/style.css` and `static/js/app.js` — responsive interface and same-origin API interactions.
- `fastapi_service/main.py` — Gemini integration, rate limiting, safe local fallback, and AI endpoints.
- `.env.example` — environment-variable template. Copy it to `.env` for local configuration.

## Django API

All user-specific API routes require a signed-in Django session. State-changing requests use Django CSRF protection. Plan reads are scoped to the signed-in owner.

- `POST /api/auth/register/`, `POST /api/auth/login/`, `POST /api/auth/logout/` — account/session operations.
- `GET /api/me/` — current session and profile status.
- `POST /api/profile/` — validate/save profile, call FastAPI, and persist the generated plan.
- `GET /api/plan/`, `GET /api/plan/<id>/` — current or selected owned plan.
- `POST /api/feedback/` — save a rating/check-in and request an updated plan.
- `GET /api/progress/`, `POST /api/progress/` — read or log progress.
- `GET /api/tips/` — return tips cached for the current day.
- `GET /api/admin/stats/` — staff-only dashboard counts and recent feedback.

## FastAPI AI API

The service accepts structured profile JSON and returns the eight requested plan sections: `summary`, `weekly_workout_plan`, `nutrition_guidance`, `daily_meal_ideas`, `hydration_and_sleep_tips`, `safety_notes`, `progress_tracking`, and `motivation`.

- `POST /api/generate/plan/` — complete structured plan.
- `POST /api/generate/workout/` — workout schedule.
- `POST /api/generate/nutrition/` — nutrition, meals, hydration and safety guidance.
- `POST /api/generate/feedback-update/` — adjust an existing plan from user feedback.
- `POST /api/generate/tips/` — personalized daily tips.
- `GET /health/` — service/provider status.

Generation requests require the shared `AI_SERVICE_TOKEN` and are limited to 30 per source IP per hour per FastAPI process. Production deployments should use a shared rate limiter/API gateway for multiple workers. Keep both services on trusted hosts; FastAPI is designed for server-to-server use and is not a public browser API.

## Database configuration

SQLite is the default and creates `db.sqlite3` in the project root. For PostgreSQL, install the included driver and set these values in `.env`:

```dotenv
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=fitbuddy
DATABASE_USER=your_database_user
DATABASE_PASSWORD=your_database_password
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432
```

For MySQL, install a compatible `mysqlclient` build in your environment, then set `DATABASE_ENGINE=django.db.backends.mysql` and the corresponding database name, user, password, host, and port. Apply migrations after switching databases.

## Production notes

Set `DJANGO_DEBUG=False`, use unique Django and AI service secrets, configure `DJANGO_ALLOWED_HOSTS`, enable HTTPS, and keep the Gemini key and database credentials in the deployment's secret store. Secure cookies and SSL redirection turn on when debug is disabled (set `DJANGO_SECURE_SSL_REDIRECT=False` only when TLS termination is handled by a trusted proxy). Configure static file serving and a production ASGI/WSGI server. Replace the in-process AI rate limiter with a shared limiter before running multiple FastAPI workers. Review calorie/macro estimates and wellness content with qualified professionals before presenting them as clinical guidance.

## Checks

```powershell
python manage.py check
python manage.py test plans.tests
python -m unittest fastapi_service.tests
```
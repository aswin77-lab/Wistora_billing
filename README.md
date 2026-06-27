# Wistora Billing

A Django-based billing application for managing customers, invoices, payments, and reports.

## Project Structure

- `core/` - Django project root
  - `manage.py` - Django command-line utility
  - `core/settings.py` - project settings and database configuration
  - `core/urls.py` - URL routing for login, dashboard, customers, invoices, payments, and reports
- `core/billing/` - main application
  - `models.py` - custom user model, customers, invoices, and payments
  - `views.py` - request handling, form actions, exports, and report generation
  - `templates/` - all HTML templates used by the app
- `AGENTS.md` - AI agent instructions for this repository
- `.gitignore` - local ignore rules

## Requirements

- Python 3.11+ (or compatible Python 3 version)
- Django 5.2.x
- MySQL database

## Local Setup

1. Create and activate a Python virtual environment.

```powershell
cd c:\Users\aswin\Downloads\wistora_billing
python -m venv venv
venv\Scripts\Activate.ps1
```

2. Install Django and required packages.

```powershell
pip install django mysqlclient
```

3. Update database settings in `core/core/settings.py` if needed.

4. Apply migrations.

```powershell
cd core
python manage.py migrate
```

5. Create a superuser.

```powershell
python manage.py createsuperuser
```

6. Run the development server.

```powershell
python manage.py runserver
```

7. Open the app in your browser at `http://127.0.0.1:8000/`.

## Notes

- The project uses a custom user model: `billing.User`.
- Only `admin` users may access customer and invoice management.
- `Invoice.save()` auto-generates invoice numbers in the format `INV-<year>-###`.
- `Payment.save()` auto-generates receipt IDs in the format `PAY-###`.
- `Invoice.update_status()` recalculates status from related payments.

## GitHub

Repository pushed to: https://github.com/aswin77-lab/Wistora_billing

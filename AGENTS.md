# AI Agent Instructions for Wistora Billing

## Project Overview
- Django billing web app located under `core/`.
- Single app: `billing`.
- Uses a custom user model at `core/billing/models.py:User` with `role` values `admin` and `accountant`.
- Templates live in `core/billing/templates/`.
- Static assets are served from `static/` and `core/static/`.

## Entrypoints & Commands
- Primary entrypoint: `core/manage.py`.
- Typical commands:
  - `cd core && python manage.py runserver`
  - `cd core && python manage.py migrate`
  - `cd core && python manage.py createsuperuser`
- No repository-level requirements file is present; inspect the active virtual environment for dependency details.

## Important Code Locations
- `core/core/settings.py`: Django settings, MySQL database config, custom user model, static files settings, login redirects.
- `core/core/urls.py`: public routes, including `login/`, `dashboard/`, `customers/`, `invoices/`, `payments/`, and `reports/`.
- `core/billing/views.py`: main application logic, form handling, authorization checks, CSV export, print/download actions.
- `core/billing/models.py`: domain models and business rules for customers, invoices, and payments.

## Domain Conventions
- `Invoice.save()` auto-generates `invoice_number` as `INV-<year>-###`.
- `Payment.save()` auto-generates `receipt_id` as `PAY-###`.
- `Invoice.update_status()` recalculates invoice `status` from related payments and saves only the status field.
- `Customer.customer_type` distinguishes `student` and `client`; student records may include `college_name` and `address`.
- Role-based access control is implemented in views: only `admin` may access customer and invoice screens.

## Notes for AI Agents
- Preserve existing business rules in models; do not break `Invoice`/`Payment` number generation or `update_status()` flow.
- When editing views, keep request handling and action dispatching in `core/billing/views.py` consistent with current GET/POST patterns.
- The app currently has no documentation files for setup or architecture, so rely on code structure and explicit settings.
- Avoid committing production secrets. `core/core/settings.py` currently contains a hardcoded Django secret key and local MySQL credentials.

## Useful Context
- The login page is served by `billing.views.login_view` and mapped to both `/` and `/login/`.
- `reports_view` uses URL query parameters for actions such as `export_csv`, `print_pdf`, `audit_trail`, and `print_receipt`.
- Template rendering is used throughout; changes to view context must match the expected template variables.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CHE GOLOSO is a Django supermarket management system (Spanish/Argentina locale) with POS, inventory, cash register, promotions, MercadoPago payments, and AI invoice scanning via Gemini Vision.

## Commands

```bash
# Development
python manage.py runserver

# Database
python manage.py makemigrations
python manage.py migrate
python manage.py setup_initial_data   # Creates default roles & payment methods (idempotent)

# Tests
python manage.py test tests                        # All tests
python manage.py test tests.test_pos_api           # Single test module
python manage.py test tests.test_pos_api.POSAPITest.test_add_item  # Single test

# Static files (production)
python manage.py collectstatic

# Environment setup
python -m venv venv
.\venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

## Architecture

**Django project**: `superrecord/` (settings, root urls, wsgi).

**Service layer pattern**: Business logic lives in `services.py` within each app, not in views. Key services:
- `pos/services.py` — `POSService`, `CartService`, `CheckoutService` (atomic checkout with stock deduction)
- `stocks/services.py` — `StockManagementService` (stock cascade through parent-child product hierarchy)
- `promotions/engine.py` — `PromotionEngine` (priority-based, combinability rules)
- `mercadopago/services.py` — `MPPointService` (Point API wrapper)
- `assistant/services.py` — `GoogleGeminiService` (invoice scanning), `BusinessDataCollector`

**Permission system**: Custom decorators in `decorators/decorators.py`:
- `@group_required(roles_list)`, `@admin_required`, `@manager_required`, `@cashier_required`, `@stock_manager_required`
- `@open_shift_required` — ensures cashier has active CashShift
- `@ajax_login_required` — returns JSON 401 for API endpoints
- Superusers bypass all group checks

**Custom User model**: `accounts.User` (extends AbstractBaseUser). Roles are Django Group proxies: Admin, Cajero Manager, Cashier, Stock Manager.

**Product hierarchy**: `Product` supports parent-child relationships for packaging (box → display → unit). `ProductPackaging` defines conversion ratios. `StockManagementService.deduct_stock_with_cascade()` propagates stock changes through the hierarchy.

**POS flow**: CashShift → POSSession → POSTransaction → POSTransactionItem + POSPayment. Ticket format: `CAJA-XX-YYYYMMDD-NNNN`. Checkout is wrapped in `@transaction.atomic`.

**MercadoPago**: Both polling (`api_check_payment_status`) and webhook (`webhook_mercadopago`) can complete a transaction — redundancy by design.

## Conventions

- Currency: Argentine format `$1.234,56` (dot=thousands, comma=decimals)
- Locale: `es-ar`, timezone `America/Argentina/Buenos_Aires`
- Brand colors: `--che-pink: #E91E8C`, `--che-purple: #2D1E5F`, `--che-yellow: #F5D000`
- POS uses dark mode (`pos-dark.css`, background `#1a1a2e`)
- Barcodes: EAN-13
- Frontend: Bootstrap 5 + Font Awesome 6, no JS framework — vanilla ES6+ with AJAX

## Database

- Development: SQLite (`db.sqlite3`)
- Production: PostgreSQL via `DATABASE_URL` env var (dj-database-url)

## Deployment

Railway with Docker. `start.sh` runs migrations → setup_initial_data → collectstatic → gunicorn. Health check at `/health/`.
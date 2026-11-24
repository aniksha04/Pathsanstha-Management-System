# Pathsanstha Management System

A Django-based cooperative credit society management system using MySQL. The project contains seven Django apps: `accounts`, `branches`, `members`, `deposits`, `transactions`, `loans`, and `reports`.

## Features

- Staff authentication and role-based access (Admin, Manager, Accountant)
- Branch management and branch-scoped workflows
- Member registration and member records
- Savings accounts, deposits, and withdrawals
- Loan applications, approval/disbursement, EMI collection, and receipts
- Transaction ledger and dashboard/report pages

## Local setup (Windows PowerShell)

1. Install Python 3.13 and MySQL Server. Create a MySQL database named `pathsanstha_db` using `utf8mb4`.
2. Create and activate a virtual environment:

   ```powershell
   py -3.13 -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and set your own local MySQL password and a private Django secret key. Do not commit `.env`.
5. Apply migrations and start the server:

   ```powershell
   python manage.py migrate
   python manage.py runserver 127.0.0.1:8001
   ```

6. Open `http://127.0.0.1:8001/`. Create an administrator account if needed with `python manage.py createsuperuser`.

## GitHub

Create an empty GitHub repository, then from this project folder run:

```powershell
git init
git add .
git status
git commit -m "Initial commit - Pathsanstha Management System"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/Pathsanstha-Management-System.git
git push -u origin main
```

Check `git status` before committing. `.env`, SQL dumps, SQLite files, virtual environments, and generated static files are excluded by `.gitignore`. Never commit real member or financial records.

## Vercel deployment

Vercel supports Django projects and detects `manage.py`. Connect this GitHub repository as a Vercel project. Before deploying, add these Environment Variables in the Vercel project settings (Production and Preview as appropriate):

- `DJANGO_SECRET_KEY` — a newly generated, private production secret
- `DJANGO_DEBUG` — `False`
- `DJANGO_ALLOWED_HOSTS` — include the deployed Vercel hostname (the settings also include `.vercel.app`)
- `CSRF_TRUSTED_ORIGINS` — the full HTTPS origin, for example `https://your-project.vercel.app`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` — credentials for a separately hosted MySQL database reachable from Vercel

Do not use your laptop's `localhost` MySQL server for the deployed site. Configure a hosted database and run `python manage.py migrate` against that database before using the deployed application. Use a separate, synthetic demo database for a public portfolio deployment; do not upload real member, account, loan, or transaction data.

Vercel serves Django static files through its CDN when `STATIC_ROOT` is configured. Review deployment logs and test login, permissions, and database-backed workflows after deployment.

## Security notes

- Keep `.env` and production credentials private.
- The project ZIP intentionally excludes the local SQLite database and SQL session dump.
- Rotate any database password or Django secret key that was previously exposed in a shared ZIP or repository.
- Do not treat a successful build as proof that production database connectivity and all workflows have been tested.

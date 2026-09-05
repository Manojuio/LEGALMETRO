# Database Design

## Overview

PostgreSQL database for the Packaged Commodities Compliance Scanner.

A single database is used. For a local prototype, a separate test database is unnecessary — tests use the same database, and demo/seed data lives alongside it.

## Connection

```
Host: localhost
Port: 5432
Database: compliance_scanner
User: postgres
Password: <set in .env — not committed>
```

### SQLAlchemy Connection URL

The `@` in the password must be URL-encoded as `%40` in a connection string:

```
postgresql://postgres:<url-encoded-password>@localhost:5432/compliance_scanner
```

## Tables

See docs/LLD.md for complete schema.

## Setup

```sql
CREATE DATABASE compliance_scanner;
```

## Seeding Demo Data

Populate the database with a sample user per role, all 17 rules, and sample products/analyses:

```bash
python -m scripts.seed_db
```

Idempotent — safe to run multiple times. Requires `DATABASE_*` values in `.env`.

## Migrations

Alembic manages database schema versioning.

```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "initial tables"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Backup

```bash
pg_dump -U postgres compliance_scanner > backup.sql
```

## Restore

```bash
psql -U postgres compliance_scanner < backup.sql
```

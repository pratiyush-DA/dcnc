# PostgreSQL Database Setup Guide

## Step 1: Install PostgreSQL

### Windows
1. Download PostgreSQL from: https://www.postgresql.org/download/windows/
2. Run the installer
3. Remember the password you set for the `postgres` user
4. Default port: 5432

### macOS
```bash
brew install postgresql
brew services start postgresql
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

## Step 2: Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE dcnc_db;

# Create user (optional, or use postgres user)
CREATE USER dcnc_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE dcnc_db TO dcnc_user;

# Exit
\q
```

## Step 3: Set Environment Variables

### Windows (PowerShell)
```powershell
$env:DATABASE_URL="postgresql://postgres:your_password@localhost:5432/dcnc_db"
$env:JWT_SECRET_KEY="your-super-secret-key-change-this-in-production"
```

### Windows (Command Prompt)
```cmd
set DATABASE_URL=postgresql://postgres:your_password@localhost:5432/dcnc_db
set JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
```

### macOS/Linux
```bash
export DATABASE_URL="postgresql://postgres:your_password@localhost:5432/dcnc_db"
export JWT_SECRET_KEY="your-super-secret-key-change-this-in-production"
```

### Or Create .env File
Create a `.env` file in the project root:
```
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/dcnc_db
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Step 4: Verify Connection

```bash
psql -U postgres -d dcnc_db -c "SELECT version();"
```

## Step 5: Initialize Database Schema

```bash
python setup_database.py
```

Or manually run the SQL schema:
```bash
psql -U postgres -d dcnc_db -f DOCUMENTATION/MULTI_TENANT_DATABASE_SCHEMA.sql
```

## Troubleshooting

### Connection Refused
- Check PostgreSQL is running: `pg_isready` or `psql -U postgres`
- Check firewall settings
- Verify port 5432 is open

### Authentication Failed
- Check username/password
- Verify pg_hba.conf allows local connections

### Database Doesn't Exist
- Run: `CREATE DATABASE dcnc_db;`

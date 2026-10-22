-- Local development role and databases. Run: make db-create (asks for the postgres password).
SELECT 'CREATE ROLE sheber LOGIN CREATEDB PASSWORD ''sheber'''
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sheber')\gexec

SELECT 'CREATE DATABASE sheber OWNER sheber'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'sheber')\gexec

-- Used by pytest (tests/conftest.py)
SELECT 'CREATE DATABASE sheber_test OWNER sheber'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'sheber_test')\gexec

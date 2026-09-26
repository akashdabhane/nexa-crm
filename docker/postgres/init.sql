-- Runs once, when the Postgres volume is first created.
-- The main database (nexa_crm) is created from POSTGRES_DB; this adds the test database.
CREATE DATABASE nexa_crm_test;

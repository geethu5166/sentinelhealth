CREATE DATABASE sentinelhealth;
\c sentinelhealth
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sentinel_migrator') THEN
        CREATE ROLE sentinel_migrator WITH LOGIN BYPASSRLS PASSWORD 'sentinel_migrator_pass_2024';
    END IF;

    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sentinel_app') THEN
        CREATE ROLE sentinel_app WITH LOGIN NOBYPASSRLS PASSWORD 'sentinel_app_pass_2024';
    END IF;
END
$$;

ALTER ROLE sentinel_migrator WITH BYPASSRLS;
ALTER ROLE sentinel_app WITH NOBYPASSRLS;

GRANT ALL PRIVILEGES ON DATABASE sentinelhealth TO sentinel_migrator;
GRANT CONNECT ON DATABASE sentinelhealth TO sentinel_app;

GRANT USAGE, CREATE ON SCHEMA public TO sentinel_migrator;
GRANT USAGE ON SCHEMA public TO sentinel_app;

ALTER DEFAULT PRIVILEGES FOR ROLE sentinel_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sentinel_app;

ALTER DEFAULT PRIVILEGES FOR ROLE sentinel_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO sentinel_app;


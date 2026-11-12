#!/bin/bash
set -e

# SentinelHealth: Database Role Separation Script
# - sentinel_migrator: DDL schema owner + BYPASSRLS for migrations/seed
# - sentinel_app: Restricted runtime user, NOBYPASSRLS, DML only
# FORCE RLS still binds table owners; migrator must BYPASSRLS for multi-tenant seed.

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "postgis";

    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${MIGRATOR_DB_USER:-sentinel_migrator}') THEN
            CREATE ROLE ${MIGRATOR_DB_USER:-sentinel_migrator} WITH LOGIN BYPASSRLS PASSWORD '${MIGRATOR_DB_PASSWORD:-sentinel_migrator_pass_2024}';
        END IF;

        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${APP_DB_USER:-sentinel_app}') THEN
            CREATE ROLE ${APP_DB_USER:-sentinel_app} WITH LOGIN NOBYPASSRLS PASSWORD '${APP_DB_PASSWORD:-sentinel_app_pass_2024}';
        END IF;
    END
    \$\$;

    -- Ensure attributes even if roles pre-existed without the intended flags.
    ALTER ROLE ${MIGRATOR_DB_USER:-sentinel_migrator} WITH BYPASSRLS;
    ALTER ROLE ${APP_DB_USER:-sentinel_app} WITH NOBYPASSRLS;

    GRANT ALL PRIVILEGES ON DATABASE "$POSTGRES_DB" TO ${MIGRATOR_DB_USER:-sentinel_migrator};
    GRANT CONNECT ON DATABASE "$POSTGRES_DB" TO ${APP_DB_USER:-sentinel_app};

    \c "$POSTGRES_DB"
    GRANT USAGE, CREATE ON SCHEMA public TO ${MIGRATOR_DB_USER:-sentinel_migrator};
    GRANT USAGE ON SCHEMA public TO ${APP_DB_USER:-sentinel_app};

    ALTER DEFAULT PRIVILEGES FOR ROLE ${MIGRATOR_DB_USER:-sentinel_migrator} IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${APP_DB_USER:-sentinel_app};

    ALTER DEFAULT PRIVILEGES FOR ROLE ${MIGRATOR_DB_USER:-sentinel_migrator} IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO ${APP_DB_USER:-sentinel_app};
EOSQL


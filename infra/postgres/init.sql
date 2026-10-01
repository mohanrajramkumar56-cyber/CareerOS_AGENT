-- CareerOS PostgreSQL initialization
-- Enables required extensions

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Ensure the careeros schema exists
-- Tables are managed by Alembic migrations

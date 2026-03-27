-- Initialise both application and test databases on first container start.
-- MySQL executes all *.sql files in /docker-entrypoint-initdb.d/ alphabetically
-- when the data directory is empty.  This script creates the test schema so that
-- the test fixtures can run alembic upgrade/downgrade without touching the live
-- transfer_bookings database.
CREATE DATABASE IF NOT EXISTS transfer_bookings_test
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON transfer_bookings_test.* TO 'root'@'%';

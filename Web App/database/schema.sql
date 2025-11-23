-- Run this script in MariaDB as the root user:
-- sudo mysql -u root -p < schema.sql

-- Create a new database for the project
CREATE DATABASE IF NOT EXISTS iot_db;

-- Create a new user that can only connect from the Pi itself
CREATE USER IF NOT EXISTS 'iot_user'@'localhost' IDENTIFIED BY 'your-strong-db-password';

-- Grant all privileges on the new database to the new user
GRANT ALL PRIVILEGES ON iot_db.* TO 'iot_user'@'localhost';

-- Apply the changes
FLUSH PRIVILEGES;
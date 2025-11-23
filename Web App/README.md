# Raspberry Pi Control Panel with Database

A Flask-based web application to display information, trigger actions, and log them to a database.

## Features

-   Web-based control panel.
-   Display details stored in a database.
-   Trigger actions with a button click.
-   All actions are logged in a database with a timestamp and status.
-   View the history of recent actions on the web page.

## Quick Start (for Development on PC)

1.  **Set up Database:** Use MySQL Workbench to create a database named `iot_control_db` and a user `iot_user` with a strong password and full privileges on that database.

2.  **Install Dependencies:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # On Windows
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    ```bash
    cp .env.example .env
    ```
    Edit `.env` and add your `SECRET_KEY` and database password.

4.  **Run the Application:**
    ```bash
    python run.py
    ```
    The app will be available at `http://127.0.0.1:5000`. The database tables will be created automatically.
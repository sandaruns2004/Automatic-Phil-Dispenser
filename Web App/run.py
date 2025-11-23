from app import create_app, db
import threading

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Import inside context to avoid circular import issues
        from app.motor_scheduler import start_motor_scheduler
        from app.motor_scheduler import buzzer_monitor

        # Start both background threads once
        threading.Thread(target=start_motor_scheduler, daemon=True).start()
        threading.Thread(target=buzzer_monitor, daemon=True).start()

    # Run Flask without creating duplicate processes
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)

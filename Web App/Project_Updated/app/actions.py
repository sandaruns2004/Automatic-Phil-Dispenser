import time
import subprocess

# --- Define your actions here ---
# Each function should return a dictionary: {'status': 'success/failed', 'message': '...'}

def trigger_blink_action():
    """Simulates an action, like blinking an LED."""
    try:
        print("ACTION TRIGGERED: Blinking an LED...")
        time.sleep(2) # Simulate work being done
        print("ACTION FINISHED.")
        return {"status": "success", "message": "Blink action completed successfully!"}
    except Exception as e:
        return {"status": "failed", "message": f"Blink action failed: {e}"}

def trigger_shutdown_action():
    """Triggers a system shutdown command."""
    # For safety, this is just a simulation.
    # To actually shutdown, you would use: subprocess.call(['sudo', 'shutdown', '-h', 'now'])
    print("ACTION TRIGGERED: Shutdown command received.")
    return {"status": "success", "message": "Shutdown command simulated. (Actual command disabled for safety)"}

def trigger_reboot_action():
    """Triggers a system reboot command."""
    # For safety, this is just a simulation.
    # To actually reboot, you would use: subprocess.call(['sudo', 'reboot'])
    print("ACTION TRIGGERED: Reboot command received.")
    return {"status": "success", "message": "Reboot command simulated. (Actual command disabled for safety)"}
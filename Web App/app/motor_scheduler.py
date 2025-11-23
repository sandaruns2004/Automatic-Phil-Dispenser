import time
import re
import subprocess
import threading
import RPi.GPIO as GPIO
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Medicine, MedicineSchedule
from datetime import datetime
import os
from RPLCD.i2c import CharLCD  # LCD import

# -------------------------------
# GPIO Setup
# -------------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


BUZZER_PIN = 23
BUTTON_PIN = 24
buzzer_active = False
stop_buzzer = False
buzzer_start_time = None

GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

lcd = CharLCD('PCF8574', address=0x27)  # change to 0x3F if needed
lcd.clear()
lcd.write_string("System Ready...")

pins_A = [17, 18, 27, 22]  # physical 11,12,13,15

# Motor B (after pin 20)
pins_B = [20, 21, 16, 26]  # physical 38,40,36,37

# Motor C (after pin 20)
pins_C = [12, 13, 19, 6]   # physical 32,33,35,31

# Map cartridge_id -> pins; change keys if your cartridge numbering differs
MOTORS = {
    1: pins_A,
    2: pins_B,
    3: pins_C
}

# Setup all motor pins
for pin_set in MOTORS.values():
    for p in pin_set:
        GPIO.setup(p, GPIO.OUT)
        GPIO.output(p, 0)

half_step_seq = [
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1],
    [1,0,0,1]
]

motor_directions = {1:1,2:1,3:1}

# -------------------------------
# Motor functions
# -------------------------------
def set_step(pins, step):
    for pin, val in zip(pins, step):
        GPIO.output(pin, val)

def rotate_motor(motor_id, steps, direction=1, delay=0.001):
    """Rotate the specified motor (by cartridge/motor id)."""
    pins = MOTORS.get(motor_id)
    if pins is None:
        print(f"[rotate_motor] No motor configured for id {motor_id}")
        return

    # Use index-based reversal to ensure direction flips correctly
    seq_len = len(half_step_seq)
    for _ in range(steps):
        if direction == 1:
            for step in half_step_seq:
                set_step(pins, step)
                time.sleep(delay)
        else:
            # iterate reversed order
            for step in reversed(half_step_seq):
                set_step(pins, step)
                time.sleep(delay)

    # turn coils off
    for p in pins:
        GPIO.output(p, 0)
# -------------------------------
# RTC Time Reader
# -------------------------------
def get_time():
    try:
        output = subprocess.check_output(["sudo", "hwclock", "-r"]).decode().strip()
        match = re.search(r"\b(\d{2}):(\d{2}):(\d{2})\b", output)
        if match:
            hour, minute, second = map(int, match.groups())
            return hour, minute, second
    except Exception as e:
        print("RTC read error:", e)
    return None, None, None

# -------------------------------
# DB Setup (adjust as per your config)
# -------------------------------
DB_URL = "mysql+pymysql://iot_user:your-strong-db-password@localhost/iot_control_db"
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)

lcd_lock = threading.Lock()

def safe_lcd_message(line1="", line2="", hold_time=4):
    """Safely update LCD from any thread."""
    with lcd_lock:
        lcd.clear()
        lcd.write_string(line1[:16])
        if line2:
            lcd.cursor_pos = (1, 0)
            lcd.write_string(line2[:16])
        time.sleep(hold_time)

def show_next_schedule_and_stock():
    """Show next medicine time and remaining stock on LCD."""
    print("Updating LCD...")
    session = Session()

    # Get next schedule (nearest future time)
    now = datetime.now().time()
    next_schedule = session.query(MedicineSchedule).filter(
        MedicineSchedule.time > now.strftime("%H:%M")
    ).order_by(MedicineSchedule.time.asc()).first()

    # Get stock info
    all_meds = session.query(Medicine).order_by(Medicine.cartridge_id.asc()).all()

    session.close()
    
    # Prepare display text
    next_text = f"Next: {next_schedule.time}" if next_schedule else "Next: None"
    stock_text = " ".join([f"C{i.cartridge_id}:{i.remaining_quantity}" for i in all_meds[:3]])
    stock_text = stock_text[:16]

    # Show safely
    safe_lcd_message(next_text, stock_text, 5)

def buzzer_monitor():
    global buzzer_active, stop_buzzer, buzzer_start_time
    
    while True:
        if buzzer_active:
            if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
                GPIO.output(BUZZER_PIN, GPIO.LOW)
                buzzer_active = False
                stop_buzzer = True
                print("Button pressed - buzzer stopped.")

                # ?? Display messages safely
                safe_lcd_message("Button pressed!", "Loading info...", 2)
                show_next_schedule_and_stock()

            # ? Auto-stop after 5 mins
            elif buzzer_start_time and (time.time() - buzzer_start_time > 300):
                GPIO.output(BUZZER_PIN, GPIO.LOW)
                buzzer_active = False
                stop_buzzer = True
                print("5-min timeout - buzzer stopped automatically.")
                
        time.sleep(0.1)
        
threading.Thread(target=buzzer_monitor, daemon=True).start()

# -------------------------------# Scheduler Thread
# -------------------------------
scheduler_running = False  # global variable

def start_motor_scheduler():
    global scheduler_running
        
    print(f"?? Process PID: {os.getpid()}, Thread count: {threading.active_count()}")
    
    if scheduler_running:
        print("Motor scheduler already running, skipping re-start.")
        return

    scheduler_running = True
    print("Starting motor scheduler thread...")

    
    def worker():
        global buzzer_active, stop_buzzer, buzzer_start_time
        last_run_time = None  # Track last processed HH:MM
        
        while True:
            hour, minute, second = get_time()
            if hour is None:
                time.sleep(10)
                continue

            now_time = f"{hour:02d}:{minute:02d}"

            # ? Skip if same minute already processed
            if now_time == last_run_time:
                time.sleep(5)
                continue
            last_run_time = now_time

            session = Session()
            schedules = session.query(MedicineSchedule).filter(
                MedicineSchedule.time == now_time
            ).all()
            
            if schedules:
                GPIO.output(BUZZER_PIN, GPIO.HIGH)
                buzzer_active = True
                stop_buzzer = False
                buzzer_start_time = time.time()
                print(f"Found {len(schedules)} schedules matching current time {now_time}.")
                print("Buzzer ON during dispensing...")

                for sched in schedules:
                    print(f"Processing schedule ID: {sched.id} (Medicine ID: {sched.medicine_id})")
                    medicine = session.query(Medicine).filter_by(id=sched.medicine_id).first()
                    if medicine and medicine.remaining_quantity > 0:
                        old_qty = medicine.remaining_quantity
                        motor_id = int(medicine.cartridge_id)
                        print(f"Medicine found: {medicine.medicine_name}, Remaining Qty: {old_qty}")
                        print(f"Dispensing {medicine.medicine_name} from cartridge {motor_id}")

                        direction = 1
                        STEPS_PER_24_DEGREES = 34

                        for dose_index in range(int(medicine.dosage)):
                            if stop_buzzer:
                                print("Stop signal received; halting remaining rotations for this schedule.")
                                break
                            print(f"  Rotation {dose_index+1}/{medicine.dosage} for motor {motor_id}, direction {direction}")
                            rotate_motor(motor_id, steps=STEPS_PER_24_DEGREES, direction=direction, delay=0.001)
                            print("  Rotation complete.")
                            time.sleep(0.5)
                            direction *= -1

                        medicine.remaining_quantity = max(0, old_qty - int(medicine.dosage))
                        session.commit()
                        print(f"Updated {medicine.medicine_name} quantity: {old_qty} ? {medicine.remaining_quantity}")
                        print("Waiting 45 seconds before next schedule (if any)...")
                time.sleep(45)

                if buzzer_active:
                    GPIO.output(BUZZER_PIN, GPIO.LOW)
                    buzzer_active = False
                    print("Buzzer turned OFF after dispensing block.")
            
            session.close()
            time.sleep(10)

    threading.Thread(target=worker, daemon=True).start()


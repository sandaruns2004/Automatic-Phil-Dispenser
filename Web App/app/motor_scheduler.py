import time
import re
import subprocess
import threading
import queue
import RPi.GPIO as GPIO
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Medicine, MedicineSchedule
from datetime import datetime
import json
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

IR_PIN = 4               # BCM pin for IR receiver
BUTTONS_FILE = "buttons.json"

# NEW: flag to indicate dispensing is in progress (prevents buzzer monitor interrupting)
dispensing_now = False

GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(IR_PIN, GPIO.IN)

# LCD setup
lcd = CharLCD('PCF8574', address=0x27)  # change to 0x3F if needed

# A dedicated queue + worker will handle all LCD writes to avoid conflicts
display_queue = queue.Queue()

pins_A = [17, 18, 27, 22]  # physical 11,12,13,15
pins_B = [20, 21, 16, 26]  # physical 38,40,36,37
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

# Timing constants for NEC
LEAD_MARK_MIN = 8000
LEAD_MARK_MAX = 10000
LEAD_SPACE_MIN = 4000
LEAD_SPACE_MAX = 5000
BIT_MARK_MIN = 400
BIT_MARK_MAX = 700
ZERO_SPACE_MAX = 800
ONE_SPACE_MIN = 1200
ONE_SPACE_MAX = 2000
FRAME_END_GAP = 0.03  # 30ms silence
COOLDOWN = 0.25

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

    for _ in range(steps):
        if direction == 1:
            for step in half_step_seq:
                set_step(pins, step)
                time.sleep(delay)
        else:
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

def load_buttons():
    if os.path.exists(BUTTONS_FILE):
        with open(BUTTONS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_buttons(buttons):
    with open(BUTTONS_FILE, "w") as f:
        json.dump(buttons, f, indent=2)

def capture_pulses(timeout_s=1.0):
    pulses = []
    last = GPIO.input(IR_PIN)
    start_time = None
    last_time = time.time()
    t0 = time.time()

    # Wait for first edge
    while True:
        cur = GPIO.input(IR_PIN)
        if cur != last:
            now = time.time()
            if start_time is None:
                start_time = now
            pulses.append(int((now - last_time) * 1_000_000))
            last_time = now
            last = cur
            break
        if time.time() - t0 > timeout_s:
            return None

    # Capture until silence
    while True:
        cur = GPIO.input(IR_PIN)
        if cur != last:
            now = time.time()
            pulses.append(int((now - last_time) * 1_000_000))
            last_time = now
            last = cur
        elif time.time() - last_time > FRAME_END_GAP:
            break
        time.sleep(0.0001)

    # **Ignore sequences too short to be NEC**
    if len(pulses) < 68:
        return None

    return pulses

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

def load_buttons():
    if os.path.exists(BUTTONS_FILE):
        with open(BUTTONS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_buttons(buttons):
    with open(BUTTONS_FILE, "w") as f:
        json.dump(buttons, f, indent=2)

def capture_pulses(timeout_s=1.0):
    pulses = []
    last = GPIO.input(IR_PIN)
    start_time = None
    last_time = time.time()
    t0 = time.time()

    # Wait for first edge
    while True:
        cur = GPIO.input(IR_PIN)
        if cur != last:
            now = time.time()
            if start_time is None:
                start_time = now
            pulses.append(int((now - last_time) * 1_000_000))
            last_time = now
            last = cur
            break
        if time.time() - t0 > timeout_s:
            return None

    # Capture until silence
    while True:
        cur = GPIO.input(IR_PIN)
        if cur != last:
            now = time.time()
            pulses.append(int((now - last_time) * 1_000_000))
            last_time = now
            last = cur
        elif time.time() - last_time > FRAME_END_GAP:
            break
        time.sleep(0.0001)

    # **Ignore sequences too short to be NEC**
    if len(pulses) < 68:
        return None

    return pulses

def find_leader(pulses):
    for i in range(len(pulses)-1):
        mark, space = pulses[i], pulses[i+1]
        if LEAD_MARK_MIN <= mark <= LEAD_MARK_MAX and LEAD_SPACE_MIN <= space <= LEAD_SPACE_MAX:
            return i
    return None

def decode_nec(pulses):
    """
    Decode NEC frame from pulses list.
    Returns integer code (32-bit) on success, else None.
    Handles noisy signals and repeats.
    """
    leader_idx = find_leader(pulses)
    if leader_idx is None:
        return None

    idx = leader_idx + 2
    bits = []

    for _ in range(32):
        if idx + 1 >= len(pulses):
            return None
        mark, space = pulses[idx], pulses[idx+1]

        # mark tolerance
        if not (BIT_MARK_MIN*0.6 <= mark <= BIT_MARK_MAX*1.6):
            return None

        # space tolerance
        if space <= ZERO_SPACE_MAX:
            bits.append(0)
        elif ONE_SPACE_MIN <= space <= ONE_SPACE_MAX:
            bits.append(1)
        else:
            # fuzzy detection
            bits.append(1 if space > (ZERO_SPACE_MAX + ONE_SPACE_MIN)/2 else 0)

        idx += 2

    # convert LSB-first bits to integer
    value = 0
    for i, b in enumerate(bits):
        if b:
            value |= (1 << i)

    # Ignore invalid all-ones codes
    if value == 0xFFFFFFFF:
        return None

    return value


def format_code_hex(code):
    return "0x{:08X}".format(code)

def get_cartridge_info(button_name):
    """
    Return the cartridge information based on button pressed
    """
    if button_name == "1":
        return "C1:A", "NEXT MED: 14.00 PM"
    elif button_name == "2":
        return "C2:B", "NEXT MED: 14.00 PM"
    elif button_name == "3":
        return "C3:B", "NEXT MED: 21.00 PM"
    else:
        return f"Button: {button_name}", ""

# -------------------------------
# LCD scrolling + display queue - FIXED VERSION
# -------------------------------
lcd_lock = threading.Lock()
display_active = False  # Flag to prevent overlapping displays

def smooth_scroll(text, width=16, cycles=2):
    """
    Return a list of frames (each exactly `width` chars).
    Smooth left-scroll: text moves left one char per frame.
    """
    if text is None:
        text = ""
    text = str(text)

    if len(text) <= width:
        # single frame, left-justified to ensure all 16 chars are overwritten
        return [text.ljust(width)]

    padding = " " * width
    t = text + padding  # allow the tail to scroll out

    frames = []
    for _ in range(cycles):
        for i in range(0, len(t) - width + 1):
            frames.append(t[i:i+width])
    return frames

def _perform_display(line1, line2, hold_time=2.0, speed=0.2):
    """
    Internal function that actually writes frames to the LCD.
    This MUST only be called from the lcd_worker thread.
    """
    global display_active
    
    # Clear LCD first to avoid any overlap
    with lcd_lock:
        lcd.clear()
        time.sleep(0.1)
    
    frames1 = smooth_scroll(line1, width=16, cycles=2)
    frames2 = smooth_scroll(line2, width=16, cycles=2)

    max_len = max(len(frames1), len(frames2))
    if len(frames1) < max_len:
        frames1 += [frames1[-1]] * (max_len - len(frames1))
    if len(frames2) < max_len:
        frames2 += [frames2[-1]] * (max_len - len(frames2))

    # Write frames without clearing to avoid flicker
    for f1, f2 in zip(frames1, frames2):
        if not display_active:  # Stop if new message arrived
            return
        with lcd_lock:
            lcd.home()
            lcd.write_string(f1[:16].ljust(16))
            lcd.cursor_pos = (1, 0)
            lcd.write_string(f2[:16].ljust(16))
        print(f"[LCD frame] '{f1}' | '{f2}'")
        time.sleep(speed)

    # Hold final frame
    hold_start = time.time()
    while time.time() - hold_start < hold_time and display_active:
        time.sleep(0.1)

def safe_lcd_message(line1="", line2="", hold_time=2.0):
    """
    Public API to show a message on the LCD.
    Clears queue and ensures only one message displays at a time.
    """
    global display_active
    
    try:
        # Stop current display
        display_active = False
        time.sleep(0.1)  # Let current display stop
        
        # Clear ALL pending messages from queue
        with display_queue.mutex:
            display_queue.queue.clear()
        
        # Start new display
        display_active = True
        display_queue.put((str(line1), str(line2) if line2 else " ", float(hold_time)))
        print(f"[LCD] queued -> '{line1[:16]}' | '{line2[:16]}' (hold {hold_time}s)")

    except Exception as e:
        print("Failed to queue LCD message:", e)
        display_active = True

def lcd_worker():
    """Background thread that serializes all LCD writes."""
    print("[LCD worker] starting")
    global display_active
    
    while True:
        try:
            item = display_queue.get()
            if item is None:
                break
                
            line1, line2, hold_time = item
            print(f"[LCD worker] displaying -> '{line1[:16]}' | '{line2[:16]}'")
            
            _perform_display(line1, line2, hold_time)
            
            display_queue.task_done()
            
        except Exception as e:
            print("LCD worker error:", e)
            time.sleep(0.5)

# Start LCD worker thread
threading.Thread(target=lcd_worker, daemon=True).start()

# Enqueue an initial ready message
safe_lcd_message("System Ready...", "Press any button", 2.0)


def ir_monitor():
    buttons = load_buttons()
    button_last_time = {}

    while True:
        if GPIO.input(IR_PIN) == 0:  # IR mark detected
            now = time.time()

            # tiny debounce to avoid noise
            if now - button_last_time.get('any', 0) < 0.05:
                time.sleep(0.01)
                continue
            button_last_time['any'] = now

            pulses = capture_pulses()
            if not pulses:
                time.sleep(0.01)
                continue

            code = decode_nec(pulses)
            if code is None or code == 0 or code == 0xFFFFFFFF:
                # skip invalid or repeat code
                time.sleep(0.01)
                continue

            hexcode = format_code_hex(code)

            # cooldown per button
            if hexcode in button_last_time and now - button_last_time[hexcode] < COOLDOWN:
                time.sleep(0.01)
                continue
            button_last_time[hexcode] = now

            # Determine button name
            if hexcode in buttons:
                name = buttons[hexcode]
            else:
                # temporary name for unknown button
                name = f"Button {hexcode[-2:]}"  
                buttons[hexcode] = name
                save_buttons(buttons)

            print(f"[IR] Detected: {name}")

            # Show cartridge information for buttons 1, 2, 3
            line1, line2 = get_cartridge_info(name)
            safe_lcd_message(line1, line2, hold_time=3.0)

        time.sleep(0.001)

# --- START IR MONITOR THREAD HERE ---
threading.Thread(target=ir_monitor, daemon=True).start()

def show_next_schedule_and_stock():
    """Show next medicine time and remaining stock on LCD via queue."""
    print("Updating LCD (show_next_schedule_and_stock)...")
    session = Session()

    now = datetime.now().time()
    next_schedule = session.query(MedicineSchedule).filter(
        MedicineSchedule.time > now.strftime("%H:%M")
    ).order_by(MedicineSchedule.time.asc()).first()

    all_meds = session.query(Medicine).order_by(Medicine.cartridge_id.asc()).all()
    session.close()
    
    next_text = f"Next: {next_schedule.time}" if next_schedule else "Next: None"
    stock_text = " ".join([f"C{i.cartridge_id}:{i.remaining_quantity}" for i in all_meds[:3]])

    # Enqueue LCD message instead of writing directly
    safe_lcd_message(next_text, stock_text, 3.0)

# -------------------------------
# Buzzer monitor
# -------------------------------
def buzzer_monitor():
    global buzzer_active, stop_buzzer, buzzer_start_time, dispensing_now
    
    while True:
        if buzzer_active:
            # Do not interrupt motor dispensing
            if dispensing_now:
                time.sleep(0.1)
                continue

            # Button pressed -> stop buzzer
            if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
                GPIO.output(BUZZER_PIN, GPIO.LOW)
                buzzer_active = False
                stop_buzzer = True
                print("Button pressed - buzzer stopped.")

                # Enqueue LCD message (lcd_worker will handle display)
                safe_lcd_message("Button pressed!", "Loading info...", 1.5)
                # Show next schedule after a short delay so LCD worker can finish
                time.sleep(2.0)
                show_next_schedule_and_stock()

            # Auto-stop after 5 mins
            elif buzzer_start_time and (time.time() - buzzer_start_time > 300):
                GPIO.output(BUZZER_PIN, GPIO.LOW)
                buzzer_active = False
                stop_buzzer = True
                print("5-min timeout - buzzer stopped automatically.")
                
        time.sleep(0.1)

threading.Thread(target=buzzer_monitor, daemon=True).start()

# -------------------------------
# Scheduler Thread
# -------------------------------
scheduler_running = False

def start_motor_scheduler():
    global scheduler_running
        
    print(f"?? Process PID: {os.getpid()}, Thread count: {threading.active_count()}")
    
    if scheduler_running:
        print("Motor scheduler already running, skipping re-start.")
        return

    scheduler_running = True
    print("Starting motor scheduler thread...")

    def worker():
        global buzzer_active, stop_buzzer, buzzer_start_time, dispensing_now
        last_run_time = None  # Track last processed HH:MM
        
        while True:
            hour, minute, second = get_time()
            if hour is None:
                time.sleep(10)
                continue

            now_time = f"{hour:02d}:{minute:02d}"

            # Skip if same minute already processed
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

                # signal that dispensing is starting (prevents buzzer monitor from interrupting)
                dispensing_now = True
                stop_buzzer = False

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
                
                dispensing_now = False
                
                time.sleep(45)

                if buzzer_active:
                    GPIO.output(BUZZER_PIN, GPIO.LOW)
                    buzzer_active = False
                    print("Buzzer turned OFF after dispensing block.")
            
            session.close()
            time.sleep(10)

    threading.Thread(target=worker, daemon=True).start()

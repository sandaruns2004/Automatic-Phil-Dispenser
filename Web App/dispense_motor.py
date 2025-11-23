# dispense_motor.py
import sys
import time

# Step 1: Check command-line arguments
if len(sys.argv) != 2:
    print("Usage: python dispense_motor.py <cartridge_num>")
    sys.exit(1)

# Step 2: Get cartridge number from arguments
try:
    cartridge_num = int(sys.argv[1])
except ValueError:
    print("Error: cartridge_num must be an integer")
    sys.exit(1)

# Step 3: Now it's safe to use or print
print(f"Dispensing tablet from Cartridge {cartridge_num}...")

# Step 4: Simulate motor action (replace with GPIO control)
time.sleep(2)

print(f"Successfully dispensed tablet from Cartridge {cartridge_num}.")

# Step 5: Exit with success
sys.exit(0)

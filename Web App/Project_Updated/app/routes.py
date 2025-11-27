from flask import Blueprint, render_template, jsonify, redirect, url_for, flash, request
from . import db
from .models import Medicine, Patient, MedicineSchedule, MedicineLog
import subprocess
from datetime import datetime

# Create Blueprint
main_bp = Blueprint('main', __name__)

# Home Page – Show all medicines with schedules
@main_bp.route('/')
def medicine_schedule():
    """Main dashboard – shows all medicines, their patients, and schedules."""
    medicines = Medicine.query.order_by(Medicine.cartridge_id).all()
    
    med_schedules = {}
    for med in medicines:
        times = [s.time for s in MedicineSchedule.query.filter_by(medicine_id=med.id).all()]
        med_schedules[med.id] = times
    
    return render_template('index.html', medicines=medicines, med_schedules=med_schedules)


# Add Patient
@main_bp.route('/patients/add', methods=['POST'])
def add_patient():
    """Add a new patient to the system."""
    name = request.form.get('name')
    age = request.form.get('age')
    password = request.form.get('password')
    guardian_contact = request.form.get('guardian_contact')

    new_patient = Patient(
        name=name,
        age=int(age),
        password=password,
        guardian_contact=guardian_contact
    )
    db.session.add(new_patient)
    db.session.commit()

    flash(f"Patient {name} added successfully!", "success")
    return redirect(url_for('main.medicine_schedule'))


#  Add or Replace Medicine
@main_bp.route('/add_medicine', methods=['POST'])
def add_medicine():
    """Add or replace a medicine for a cartridge, linked to a patient."""
    cartridge_num = int(request.form.get('cartridge_num'))
    patient_id = 1  # Default patient (you can update later)
    name = request.form.get('medicine_name')
    dosage = request.form.get('dosage')
    remaining = int(request.form.get('remaining'))
    times = request.form.getlist('times')  # List of dispense times

    # Check if a medicine already exists in the same cartridge
    existing_med = Medicine.query.filter_by(cartridge_id=cartridge_num).first()

    if existing_med:
        # 1?? Delete all schedules of the existing medicine
        MedicineSchedule.query.filter_by(medicine_id=existing_med.id).delete()
        db.session.commit()  # Commit deletion first to avoid FK issues

        # 2?? Delete the existing medicine
        db.session.delete(existing_med)
        db.session.commit()

        msg = f"Cartridge {cartridge_num} updated with new medicine '{name}'."
    else:
        msg = f"Added '{name}' to Cartridge {cartridge_num}."

    # 3?? Add new medicine
    new_med = Medicine(
        cartridge_id=cartridge_num,
        patient_id=patient_id,
        medicine_name=name,
        dosage=dosage,
        remaining_quantity=remaining,
        last_action="Pending"
    )
    db.session.add(new_med)
    db.session.commit()  # Commit to get new_med.id

    # 4?? Add new schedule times (one record per time)
    for t in times:
        schedule = MedicineSchedule(medicine_id=new_med.id, time=t)
        db.session.add(schedule)
    db.session.commit()

    flash(msg, "success")
    return redirect(url_for('main.medicine_schedule'))


# Add Schedule for Existing Medicine
@main_bp.route('/add_schedule', methods=['POST'])
def add_schedule():
    """Add an additional time schedule for an existing medicine."""
    medicine_id = int(request.form.get('medicine_id'))
    time = request.form.get('time')

    new_sched = MedicineSchedule(medicine_id=medicine_id, time=time)
    db.session.add(new_sched)
    db.session.commit()

    flash(f"Added new schedule ({time}) for medicine ID {medicine_id}.", "success")
    return redirect(url_for('main.medicine_schedule'))


# Take Medicine (mark dose taken + log it)
@main_bp.route('/api/medicine/take/<int:medicine_id>', methods=['POST'])
def api_take_medicine(medicine_id):
    """When patient takes a dose manually."""
    medicine = Medicine.query.get_or_404(medicine_id)

    if medicine.remaining_quantity > 0:
        medicine.remaining_quantity -= 1
        medicine.last_action = f"Dose Taken ({datetime.now().strftime('%H:%M')})"

        # Log action
        log = MedicineLog(medicine_id=medicine.id, action="Dose Taken")
        db.session.add(log)
        db.session.commit()

        # TODO: integrate guardian notification here
        # notify_guardian(medicine.patient.guardian_contact, f"{medicine.medicine_name} dose taken.")

        return jsonify({
            "status": "success",
            "message": f"Dose of {medicine.medicine_name} taken.",
            "remaining": medicine.remaining_quantity
        })
    else:
        return jsonify({
            "status": "error",
            "message": f"No remaining quantity for {medicine.medicine_name}."
        }), 400


# Dispense Medicine (trigger hardware)
@main_bp.route('/dispense_medicine', methods=['POST'])
def dispense_medicine():
    """Dispense tablet using motor control (by cartridge)."""
    cartridge_num = int(request.form.get('cartridge_num'))

    try:
        subprocess.run(['python3', 'dispense_motor.py', str(cartridge_num)], check=True)

        # Log action
        med = Medicine.query.filter_by(cartridge_id=cartridge_num).first()
        if med:
            med.last_action = "Dispensed"
            med.remaining_quantity -= 1
            db.session.add(MedicineLog(medicine_id=med.id, action="Dispensed"))
            db.session.commit()

        flash(f"Successfully dispensed tablet from Cartridge {cartridge_num}.", "success")
    except subprocess.CalledProcessError:
        flash(f"Failed to dispense from Cartridge {cartridge_num}.", "danger")

    return redirect(url_for('main.medicine_schedule'))


from flask import request, redirect, url_for, flash

@main_bp.route('/update_time', methods=['POST'])
def update_time():
    medicine_id = request.form.get('medicine_id')  # medicine table ID
    dispense_times = request.form.getlist('dispense_times[]')  # list of times

    if not medicine_id or not dispense_times:
        flash("Please select a medicine and provide at least one time.", "danger")
        return redirect(url_for('main.medicine_schedule'))

    medicine = Medicine.query.get(medicine_id)
    if not medicine:
        flash("Selected medicine not found.", "danger")
        return redirect(url_for('main.medicine_schedule'))

    # Remove existing schedule records for this medicine
    from .models import MedicineSchedule
    MedicineSchedule.query.filter_by(medicine_id=medicine_id).delete()

    # Add new schedule records
    for t in dispense_times:
        new_schedule = MedicineSchedule(
            medicine_id=medicine_id,
            time=t
        )
        db.session.add(new_schedule)

    db.session.commit()

    flash(f"Dispense times for '{medicine.medicine_name}' have been updated.", "success")
    return redirect(url_for('main.medicine_schedule'))



@main_bp.route('/api/medicine_times/<int:medicine_id>')
def get_medicine_times(medicine_id):
    from .models import MedicineSchedule, Medicine

    medicine = Medicine.query.get_or_404(medicine_id)
    schedules = MedicineSchedule.query.filter_by(medicine_id=medicine_id).all()

    # Convert time to string (HH:MM format)
    times_info = [
        {"time": s.time.strftime("%H:%M") if hasattr(s.time, "strftime") else str(s.time),
         "cartridge_id": medicine.cartridge_id}
        for s in schedules
    ]

    return jsonify({"times": times_info})
    
@main_bp.route('/api/medicines')
def api_get_medicines():
    """Return all medicines with current remaining quantities."""
    medicines = Medicine.query.order_by(Medicine.cartridge_id).all()
    data = []
    for med in medicines:
        data.append({
            "id": med.id,
            "name": med.medicine_name,
            "cartridge_id": med.cartridge_id,
            "remaining_quantity": med.remaining_quantity
        })
    return jsonify(data)



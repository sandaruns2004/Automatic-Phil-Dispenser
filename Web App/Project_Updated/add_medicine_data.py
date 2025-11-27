from app import create_app, db
from app.models import Medicine

app = create_app()

with app.app_context():
    print("Adding sample medicine data...")
    
    # Check if data already exists
    if Medicine.query.first():
        print("Data already exists. Skipping.")
    else:
        # Create sample medicine records
        med1 = Medicine(cartridge_id=101, medicine_name='Aspirin', dosage='100mg', time='08:00 AM', remaining_quantity=25,last_action = 'Completed')
        med2 = Medicine(cartridge_id=102, medicine_name='Vitamin D', dosage='5000 IU', time='09:00 AM', remaining_quantity=60,last_action = 'Pending')
        med3 = Medicine(cartridge_id=103, medicine_name='Metformin', dosage='500mg', time='After Lunch', remaining_quantity=40 , last_action = 'Dispensed')
        med4 = Medicine(cartridge_id=104, medicine_name='Lisinopril', dosage='10mg', time='08:00 PM', remaining_quantity=15, last_action = 'Completed')

        # Add to the database session
        db.session.add(med1)
        db.session.add(med2)
        db.session.add(med3)
        db.session.add(med4)

        # Commit the changes
        db.session.commit()
        print("Sample data added successfully!")

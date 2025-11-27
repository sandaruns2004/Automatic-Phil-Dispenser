from . import db

class Patient(db.Model):
    __tablename__ = 'patients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    guardian_contact = db.Column(db.String(50), nullable=False)

    medicines = db.relationship('Medicine', backref='patient', lazy=True)


class Medicine(db.Model):
    __tablename__ = 'medicines'
    id = db.Column(db.Integer, primary_key=True)
    cartridge_id = db.Column(db.Integer, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    medicine_name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.Integer, nullable=False)
    remaining_quantity = db.Column(db.Integer, nullable=False)
    last_action = db.Column(db.String(50), default='N/A')

    schedules = db.relationship('MedicineSchedule', backref='medicine', lazy=True)
    logs = db.relationship('MedicineLog', backref='medicine', lazy=True)


class MedicineSchedule(db.Model):
    __tablename__ = 'medicine_schedule'
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    time = db.Column(db.String(50), nullable=False)


class MedicineLog(db.Model):
    __tablename__ = 'medicine_logs'
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

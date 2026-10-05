import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

# --- 1. SQL DATABASE SETUP ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patients.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    # Feature 6: Emergency details stored in SQL
    emergency_contact = db.Column(db.String(20), nullable=True)
    blood_group = db.Column(db.String(10), nullable=True)

# --- 2. MONGODB SETUP ---
mongo_client = MongoClient(os.environ.get('MONGO_URI'))
mongo_db = mongo_client['elderly_care']
medication_collection = mongo_db['medications']

# --- 3. ROUTES ---
@app.route('/')
def home():
    all_patients = Patient.query.all()
    all_meds = list(medication_collection.find())
    
    # Feature 4: Calculate adherence compliance rate
    total_logs = len(all_meds)
    taken_logs = sum(1 for m in all_meds if m.get('status') == 'Taken')
    compliance_rate = round((taken_logs / total_logs) * 100) if total_logs > 0 else 100

    return render_template(
        'index.html', 
        patients=all_patients, 
        medications=all_meds, 
        compliance=compliance_rate
    )

@app.route('/add_patient', methods=['POST'])
def add_patient():
    patient_name = request.form.get('name')
    patient_age = request.form.get('age')
    emergency_contact = request.form.get('emergency_contact')
    blood_group = request.form.get('blood_group')
    
    new_patient = Patient(
        name=patient_name, 
        age=patient_age, 
        emergency_contact=emergency_contact, 
        blood_group=blood_group
    )
    try:
        db.session.add(new_patient)
        db.session.commit()
    except:
        db.session.rollback()
        
    return redirect(url_for('home'))

@app.route('/add_medication', methods=['POST'])
def add_medication():
    patient_name = request.form.get('patient_name')
    med_name = request.form.get('med_name')
    dosage = request.form.get('dosage')
    med_time = request.form.get('med_time')
    
    medication_document = {
        "patient_name": patient_name,
        "medicine": med_name,
        "dosage": dosage,
        "time": med_time,
        "status": "Pending"  # Default status for tracking
    }
    medication_collection.insert_one(medication_document)
    return redirect(url_for('home'))

# Feature 4: Route to update Taken/Skipped status
@app.route('/update_status/<med_id>/<new_status>')
def update_status(med_id, new_status):
    medication_collection.update_one(
        {"_id": ObjectId(med_id)},
        {"$set": {"status": new_status}}
    )
    return redirect(url_for('home'))
# Move this part outside so Gunicorn reads it!
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run()

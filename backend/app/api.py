from backend.app.database import get_db_connection


import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.database import get_db_connection

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def query(sql):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [c[0] for c in cur.description]
        rows = [r if isinstance(r, dict) else dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
        return json.loads(json.dumps(rows, default=str))
    finally:
        conn.close()


@app.get("/api/doctors")
def doctors():
    return query("""
        SELECT d.doctor_id, d.doctor_name, d.specialization, d.consultation_fee,
               (SELECT COUNT(*) FROM doctor_slots s
                 WHERE s.doctor_id = d.doctor_id AND s.slot_date = CURDATE()
                   AND NOT EXISTS (SELECT 1 FROM appointments a
                                    WHERE a.slot_id = s.slot_id AND a.status = 'BOOKED')
               ) AS open_today,
               (SELECT COUNT(*) FROM doctor_slots s
                 WHERE s.doctor_id = d.doctor_id AND s.slot_date >= CURDATE()
                   AND NOT EXISTS (SELECT 1 FROM appointments a
                                    WHERE a.slot_id = s.slot_id AND a.status = 'BOOKED')
               ) AS open_slots
        FROM doctors d
        ORDER BY d.doctor_id
    """)


@app.get("/api/appointments")
def appointments():
    return query("""
        SELECT a.appointment_id, a.patient_name, a.patient_phone, a.status,
               d.doctor_name,
               s.slot_date AS appointment_date,
               s.start_time AS appointment_time
        FROM appointments a
        JOIN doctor_slots s ON a.slot_id = s.slot_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        ORDER BY a.appointment_id DESC
        LIMIT 50
    """)
@app.get("/api/slots")
def slots():
    return query("""
        SELECT s.slot_id, s.doctor_id, s.slot_date, s.start_time
        FROM doctor_slots s
        WHERE (s.slot_date > CURDATE()
               OR (s.slot_date = CURDATE() AND s.start_time > CURTIME()))
          AND NOT EXISTS (SELECT 1 FROM appointments a
                          WHERE a.slot_id = s.slot_id AND a.status = 'BOOKED')
        ORDER BY s.slot_date, s.start_time
    """)
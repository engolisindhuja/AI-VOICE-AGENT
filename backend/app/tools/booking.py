
from backend.app.database import get_db_connection


def book_appointment(
    patient_name,
    patient_phone,
    doctor_id,
    slot_id
):
    connection = get_db_connection()

    if connection is None:
        return {"success": False, "message": "Database connection failed."}

    cursor = None

    try:
        connection.start_transaction()

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT slot_id, doctor_id, slot_date, start_time, status
            FROM doctor_slots
            WHERE slot_id = %s
              AND doctor_id = %s
            FOR UPDATE
            """,
            (slot_id, doctor_id)
        )

        slot = cursor.fetchone()

        if not slot:
            connection.rollback()
            return {"success": False, "message": "Invalid slot or doctor."}

        if slot["status"] != "AVAILABLE":
            connection.rollback()
            return {"success": False, "message": "This slot is already booked."}

        cursor.execute(
            """
            INSERT INTO appointments (
                patient_name,
                patient_phone,
                doctor_id,
                slot_id,
                appointment_date,
                appointment_time,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'BOOKED')
            """,
            (
                patient_name,
                patient_phone,
                doctor_id,
                slot_id,
                slot["slot_date"],
                slot["start_time"]
            )
        )

        appointment_id = cursor.lastrowid

        cursor.execute(
            """
            UPDATE doctor_slots
            SET status = 'BOOKED'
            WHERE slot_id = %s
              AND status = 'AVAILABLE'
            """,
            (slot_id,)
        )

        if cursor.rowcount != 1:
            connection.rollback()
            return {"success": False, "message": "Slot booking failed."}

        connection.commit()

        return {
            "success": True,
            "message": "Appointment booked successfully.",
            "appointment_id": appointment_id,
            "patient_name": patient_name,
            "doctor_id": doctor_id,
            "slot_id": slot_id,
            "appointment_date": str(slot["slot_date"]),
            "appointment_time": str(slot["start_time"])
        }

    except Exception as e:
        connection.rollback()
        return {"success": False, "message": str(e)}

    finally:
        if cursor:
            cursor.close()

        connection.close()

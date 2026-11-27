
from backend.app.database import get_db_connection
from mysql.connector import Error


def cancel_appointment(appointment_id, patient_phone):


    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Database connection failed."
            }

        cursor = connection.cursor(dictionary=True)

        
        cursor.execute(
            """
            SELECT appointment_id, patient_name, patient_phone,
                   slot_id, appointment_date, appointment_time, status
            FROM appointments
            WHERE appointment_id = %s
              AND patient_phone = %s
            """,
            (appointment_id, patient_phone)
        )

        appointment = cursor.fetchone()

        if appointment is None:
            return {
                "success": False,
                "message": "No appointment found with this appointment ID and phone number."
            }

        if appointment["status"] == "CANCELLED":
            return {
                "success": False,
                "message": "This appointment has already been cancelled."
            }

        cursor.execute(
            """
            UPDATE appointments
            SET status = 'CANCELLED'
            WHERE appointment_id = %s
              AND patient_phone = %s
              AND status = 'BOOKED'
            """,
            (appointment_id, patient_phone)
        )

        if cursor.rowcount != 1:
            connection.rollback()
            return {
                "success": False,
                "message": "Appointment could not be cancelled."
            }

        cursor.execute(
            """
            UPDATE doctor_slots
            SET status = 'AVAILABLE'
            WHERE slot_id = %s
            """,
            (appointment["slot_id"],)
        )

        connection.commit()

        return {
            "success": True,
            "message": "Appointment cancelled successfully.",
            "appointment_id": appointment["appointment_id"],
            "patient_name": appointment["patient_name"],
            "appointment_date": str(appointment["appointment_date"]),
            "appointment_time": str(appointment["appointment_time"])
        }

    except Error as e:
        if connection:
            connection.rollback()

        return {
            "success": False,
            "message": f"Database error: {str(e)}"
        }

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

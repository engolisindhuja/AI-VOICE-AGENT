from backend.app.database import get_db_connection


def check_doctor_availability(
    doctor_id=None,
    slot_date=None,
    specialization=None
):
    connection = get_db_connection()

    if connection is None:
        print("Database connection failed.")
        return []

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                d.doctor_id,
                d.doctor_name,
                d.specialization,
                d.consultation_fee,
                s.slot_id,
                s.slot_date,
                s.start_time,
                s.end_time
            FROM doctors d
            JOIN doctor_slots s
                ON d.doctor_id = s.doctor_id
            WHERE d.is_active = 1
              AND s.status = 'AVAILABLE'
              AND s.slot_date >= CURDATE()
        """

        values = []

        if doctor_id is not None:
            query += " AND d.doctor_id = %s"
            values.append(doctor_id)

        if slot_date is not None:
            query += " AND s.slot_date = %s"
            values.append(slot_date)

        if specialization is not None:
            query += " AND d.specialization LIKE %s"
            values.append(f"%{specialization}%")

        query += """
            ORDER BY s.slot_date, s.start_time
        """

        cursor.execute(query, tuple(values))

        return cursor.fetchall()

    except Exception as e:
        print("Availability Error:", e)
        return []

    finally:
        if cursor:
            cursor.close()
        connection.close()

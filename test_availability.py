
from backend.app.database import get_db_connection

try:
    connection = get_db_connection()

    print("MySQL Connected Successfully!")

    cursor = connection.cursor(dictionary=True)

    doctor_id = 1

    query = """
        SELECT slot_id, doctor_id, slot_date, start_time, end_time
        FROM doctor_slots
        WHERE doctor_id = %s
        AND status = 'AVAILABLE'
        ORDER BY slot_date, start_time
        LIMIT 10
    """

    cursor.execute(query, (doctor_id,))
    slots = cursor.fetchall()

    print("\nAvailable Doctor Slots:")

    if slots:
        for slot in slots:
            print(slot)
    else:
        print("No available slots found.")

    cursor.close()
    connection.close()

except Exception as e:
    print("Error:", e)

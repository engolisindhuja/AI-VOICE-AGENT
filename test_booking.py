
import sys
import os

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "backend")
)

from backend.app.tools.availability import check_doctor_availability
from backend.app.tools.booking import book_appointment

slots = check_doctor_availability(doctor_id=1)

if not slots:
    print("No available slots for testing.")
else:
    selected_slot = slots[0]

    print("\nSelected slot:")
    print(selected_slot)

    result = book_appointment(
        patient_name="Test Patient",
        patient_phone="9999999999",
        doctor_id=selected_slot["doctor_id"],
        slot_id=selected_slot["slot_id"]
    )

    print("\nBooking Result:")
    print(result)

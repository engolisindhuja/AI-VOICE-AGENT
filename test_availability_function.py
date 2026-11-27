
import sys
import os

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "backend")
)

from backend.app.tools.availability import check_doctor_availability


if __name__ == "__main__":

    print("\nChecking doctor availability...\n")

    results = check_doctor_availability()

    if results:
        for doctor in results:
            print("------------------------------")
            print("Doctor:", doctor["doctor_name"])
            print("Specialization:", doctor["specialization"])
            print("Fee:", doctor["consultation_fee"])
            print("Date:", doctor["slot_date"])
            print("Start:", doctor["start_time"])
            print("End:", doctor["end_time"])
            print("Slot ID:", doctor["slot_id"])
    else:
        print("No available doctor slots found.")

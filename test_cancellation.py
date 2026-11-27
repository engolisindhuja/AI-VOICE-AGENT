
from backend.app.tools.cancellation import cancel_appointment

print("===== APPOINTMENT CANCELLATION TEST =====")

appointment_id = int(input("Enter Appointment ID: "))
patient_phone = input("Enter Patient Phone Number: ").strip()

result = cancel_appointment(appointment_id, patient_phone)

print("\nCancellation Result:")
print(result)

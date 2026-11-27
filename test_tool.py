from backend.app.tools.availability import check_doctor_availability

print("1:", check_doctor_availability(slot_date="2026-11-27"))
print("2:", check_doctor_availability(specialization="Dermatologist"))
print("3:", check_doctor_availability())
from fastapi import FastAPI
from routers import patients, doctors, appointments

app = FastAPI(title="CityMed Hospital Appointment API")
app.include_router(patients.router)
app.include_router(doctors.router)
app.include_router(appointments.router)


@app.get("/health")
async def health():
    from database import supabase
    p = supabase.table("patients").select(
        "patient_id", count="exact").execute()
    d = supabase.table("doctors").select("doctor_id", count="exact").execute()
    a = supabase.table("appointments").select(
        "appointment_id", count="exact").execute()
    return {"status": "ok", "patients": p.count, "doctors": d.count, "appointments": a.count}

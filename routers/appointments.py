from fastapi import APIRouter, Query, Path, Depends
from datetime import datetime, date as date_type
from database import supabase
from schemas import CreateAppointmentRequest
from errors import error_response
from auth import verify_token
from specialty_rules import validate_booking, generate_confirmation_code

router = APIRouter(prefix="/v1/appointments", tags=["Appointments"])


@router.get("")
async def get_appointments(
    patient_id: str = Query(...),
    status: str = Query("all"),
    sort: str | None = Query(None),
    limit: int = Query(10, ge=1),
    _=Depends(verify_token)
):
    if status not in ["upcoming", "completed", "cancelled", "all"]:
        return error_response(400, "INVALID_STATUS", "Invalid appointment status.")

    query = supabase.table("appointments").select(
        "*").eq("patient_id", patient_id)
    if status != "all":
        query = query.eq("status", status)

    order_dir = sort if sort in ["asc", "desc"] else (
        "desc" if status == "completed" else "asc")
    query = query.order("slot_datetime", desc=(
        order_dir == "desc")).limit(limit)

    result = query.execute()
    appointments = result.data

    doctor_ids = list({a["doctor_id"]
                      for a in appointments if a.get("doctor_id")})
    doctor_names = {}
    if doctor_ids:
        doctors = supabase.table("doctors").select(
            "doctor_id, full_name").in_("doctor_id", doctor_ids).execute()
        doctor_names = {d["doctor_id"]: d["full_name"] for d in doctors.data}
    for a in appointments:
        a["doctor_name"] = doctor_names.get(a["doctor_id"])

    return {"total": len(appointments), "appointments": appointments}


@router.post("", status_code=201)
async def book_appointment(body: CreateAppointmentRequest, _=Depends(verify_token)):
    if body.appointment_type == "follow_up" and not body.linked_appointment_id:
        return error_response(400, "MISSING_LINKED_APPOINTMENT", "linked_appointment_id is required for follow_up appointments.")

    patient = supabase.table("patients").select(
        "patient_id").eq("patient_id", body.patient_id).execute()
    if not patient.data:
        return error_response(400, "PATIENT_NOT_FOUND", "No patient found for patient_id.")

    doctor = supabase.table("doctors").select(
        "*").eq("doctor_id", body.doctor_id).execute()
    if not doctor.data:
        return error_response(404, "DOCTOR_NOT_FOUND", "No doctor found for that ID.")
    doctor_row = doctor.data[0]

    specialty_row = supabase.table("specialties").select(
        "*").eq("name", body.specialty).execute()
    if not specialty_row.data:
        return error_response(400, "INVALID_SPECIALTY", "Specialty must match an allowed CityMed specialty.")
    specialty = specialty_row.data[0]

    slot_dt = datetime.fromisoformat(body.slot_datetime)
    error_code, error_message = validate_booking(
        specialty, body, slot_dt.date())
    if error_code:
        return error_response(400, error_code, error_message)

    # doctor-side conflict check
    doctor_conflict = (
        supabase.table("appointments")
        .select("appointment_id")
        .eq("doctor_id", body.doctor_id)
        .eq("slot_datetime", body.slot_datetime)
        .eq("status", "upcoming")
        .execute()
    )
    if doctor_conflict.data:
        return error_response(409, "SLOT_TAKEN", "That slot was just taken by another patient.")

    # patient-side conflict check
    patient_conflict = (
        supabase.table("appointments")
        .select("appointment_id")
        .eq("patient_id", body.patient_id)
        .eq("slot_datetime", body.slot_datetime)
        .eq("status", "upcoming")
        .execute()
    )
    if patient_conflict.data:
        return error_response(409, "PATIENT_SLOT_CONFLICT", f"You already have an appointment with {doctor_row['full_name']} at this time slot.")

    duration = body.slot_duration_minutes or doctor_row["slot_duration_minutes"]
    confirmation_code = generate_confirmation_code()

    insert = supabase.table("appointments").insert({
        "patient_id": body.patient_id,
        "doctor_id": body.doctor_id,
        "specialty": body.specialty,
        "appointment_type": body.appointment_type,
        "slot_datetime": body.slot_datetime,
        "slot_duration_minutes": duration,
        "specialty_notes": body.specialty_notes or "",
        "linked_appointment_id": body.linked_appointment_id,
        "confirmation_code": confirmation_code
    }).execute()

    appointment = insert.data[0]

    return {
        "appointment_id": appointment["appointment_id"],
        "confirmation_code": confirmation_code,
        "doctor_name": doctor_row["full_name"],
        "specialty": body.specialty,
        "slot_datetime": body.slot_datetime,
        "status": "upcoming",
        "hospital_location": "CityMed Hospital, Block A, Ground Floor, Registration Counter 3",
        "appointment": appointment
    }


@router.patch("/{appointment_id}/cancel")
async def cancel_appointment(appointment_id: str = Path(...), body: dict = None, _=Depends(verify_token)):
    existing = supabase.table("appointments").select(
        "*").eq("appointment_id", appointment_id).execute()
    if not existing.data:
        return error_response(404, "APPOINTMENT_NOT_FOUND", "Appointment not found.")

    appt = existing.data[0]

    if appt["status"] != "upcoming":
        return error_response(409, "APPOINTMENT_NOT_CANCELLABLE", "Appointment is already cancelled or completed.")

    if datetime.fromisoformat(appt["slot_datetime"]) < datetime.now(datetime.fromisoformat(appt["slot_datetime"]).tzinfo):
        return error_response(400, "PAST_APPOINTMENT", "Appointment is in the past and cannot be cancelled.")

    reason = (body or {}).get("cancellation_reason") if body else None

    updated = (
        supabase.table("appointments")
        .update({
            "status": "cancelled",
            "cancelled_at": datetime.utcnow().isoformat(),
            "cancellation_reason": reason
        })
        .eq("appointment_id", appointment_id)
        .execute()
    )

    doctor = supabase.table("doctors").select("full_name").eq(
        "doctor_id", appt["doctor_id"]).execute()
    doctor_name = doctor.data[0]["full_name"] if doctor.data else None

    result = updated.data[0]
    return {
        "appointment_id": appointment_id,
        "status": "cancelled",
        "cancelled_at": result["cancelled_at"],
        "cancellation_reason": reason,
        "doctor_name": doctor_name,
        "slot_datetime": appt["slot_datetime"]
    }

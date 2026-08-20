from slot_utils import generate_day_slots, DAY_MAP
from fastapi import Path
from datetime import datetime, date as date_type
from fastapi import APIRouter, Query, Depends
from database import supabase
from errors import error_response
from auth import verify_token

router = APIRouter(prefix="/v1/doctors", tags=["Doctors"])

VALID_SPECIALTIES = [
    "General Physician", "Dentistry", "Orthopedics", "Cardiology",
    "Dermatology", "Pediatrics", "Gynecology", "Neurology",
    "Ophthalmology", "ENT"
]


@router.get("")
async def get_doctors(specialty: str = Query(...), active_only: bool = True, _=Depends(verify_token)):
    matched = next((s for s in VALID_SPECIALTIES if s.lower()
                   == specialty.lower()), None)
    if not matched:
        return error_response(400, "INVALID_SPECIALTY", "Specialty must match an allowed CityMed specialty.")

    specialty_row = supabase.table("specialties").select(
        "id").eq("name", matched).execute()
    if not specialty_row.data:
        return error_response(400, "INVALID_SPECIALTY", "Specialty must match an allowed CityMed specialty.")

    specialty_id = specialty_row.data[0]["id"]

    query = supabase.table("doctors").select(
        "*").eq("specialty_id", specialty_id)
    if active_only:
        query = query.eq("active", True)

    result = query.execute()

    doctors = [
        {
            "doctor_id": d["doctor_id"],
            "full_name": d["full_name"],
            "specialty": matched,
            "sub_specialty": d.get("sub_specialty"),
            "available_days": d["available_days"],
            "slot_duration_minutes": d["slot_duration_minutes"],
            "advance_booking_days": d["advance_booking_days"],
            "active": d["active"]
        }
        for d in result.data
    ]

    return {"specialty": matched, "doctors": doctors}


@router.get("/{doctor_id}/slots")
async def get_doctor_slots(
    doctor_id: str = Path(...),
    date: str = Query(...),
    time_pref: str = Query("any"),
    _=Depends(verify_token)
):
    try:
        requested_date = date_type.fromisoformat(date)
    except ValueError:
        return error_response(400, "INVALID_DATE", "Date must be YYYY-MM-DD.")

    doctor_row = supabase.table("doctors").select(
        "*").eq("doctor_id", doctor_id).execute()
    if not doctor_row.data:
        return error_response(404, "DOCTOR_NOT_FOUND", "No doctor found for that ID.")

    doctor = doctor_row.data[0]
    weekday = DAY_MAP[requested_date.weekday()]

    if weekday not in doctor["available_days"]:
        return {
            "doctor_id": doctor_id,
            "doctor_name": doctor["full_name"],
            "date": date,
            "slots": []
        }

    candidate_times = generate_day_slots(
        doctor["slot_duration_minutes"], time_pref)

    existing = (
        supabase.table("appointments")
        .select("slot_datetime")
        .eq("doctor_id", doctor_id)
        .eq("status", "upcoming")
        .gte("slot_datetime", f"{date}T00:00:00")
        .lte("slot_datetime", f"{date}T23:59:59")
        .execute()
    )
    booked_times = {
        datetime.fromisoformat(a["slot_datetime"]).time() for a in existing.data
    }

    now = datetime.now()
    slots = []
    for t in candidate_times:
        slot_dt = datetime.combine(requested_date, t)
        is_past = slot_dt < now
        is_booked = t in booked_times
        slots.append({
            "slot_datetime": slot_dt.isoformat() + "+05:30",
            "available": not is_past and not is_booked,
            "duration_minutes": doctor["slot_duration_minutes"],
            "slot_duration_minutes": doctor["slot_duration_minutes"],
            "doctor_id": doctor_id,
            "doctor_name": doctor["full_name"]
        })

    return {
        "doctor_id": doctor_id,
        "doctor_name": doctor["full_name"],
        "date": date,
        "slots": slots
    }

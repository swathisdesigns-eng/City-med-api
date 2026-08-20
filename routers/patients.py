from fastapi import APIRouter, Query, Depends
from database import supabase
from schemas import CreatePatientRequest
from errors import error_response
from phone_utils import normalize_phone
from auth import verify_token

router = APIRouter(prefix="/v1/patients", tags=["Patients"])


@router.get("")
async def get_patients(phone: str = Query(...), name: str | None = None, _=Depends(verify_token)):
    normalized = normalize_phone(phone)
    if not normalized:
        return error_response(400, "INVALID_PHONE", "Phone number must be E.164 formatted.", {"received": phone})

    query = supabase.table("patients").select(
        "*").eq("phone_number", normalized)
    if name:
        query = query.ilike("full_name", f"%{name}%")

    result = query.execute()
    return {"count": len(result.data), "patients": result.data}


@router.post("", status_code=201)
async def create_patient(body: CreatePatientRequest, _=Depends(verify_token)):
    normalized = normalize_phone(body.phone_number)
    if not normalized:
        return error_response(400, "INVALID_PHONE", "Phone number must be E.164 formatted.", {"received": body.phone_number})

    existing = (
        supabase.table("patients")
        .select("patient_id")
        .eq("phone_number", normalized)
        .eq("full_name", body.full_name)
        .execute()
    )
    if existing.data:
        return error_response(
            409, "PATIENT_ALREADY_EXISTS", "A matching patient already exists.",
            {"patient_id": existing.data[0]["patient_id"]}
        )

    insert = supabase.table("patients").insert({
        "full_name": body.full_name,
        "phone_number": normalized,
        "date_of_birth": str(body.date_of_birth),
        "gender": body.gender,
        "email": body.email,
        "insurance_id": body.insurance_id
    }).execute()

    patient = insert.data[0]
    return {"patient_id": patient["patient_id"], "patient": patient}

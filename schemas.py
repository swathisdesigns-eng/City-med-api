from pydantic import BaseModel
from typing import Optional, Literal
from datetime import date, datetime


class Patient(BaseModel):
    patient_id: str
    full_name: str
    phone_number: str
    date_of_birth: date
    gender: Literal["M", "F", "Other"]
    email: Optional[str] = ""
    insurance_id: Optional[str] = ""
    created_at: Optional[datetime] = None


class CreatePatientRequest(BaseModel):
    full_name: str
    phone_number: str
    date_of_birth: date
    gender: Literal["M", "F", "Other"]
    email: Optional[str] = ""
    insurance_id: Optional[str] = ""


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Doctor(BaseModel):
    doctor_id: str
    full_name: str
    specialty: str
    sub_specialty: Optional[str] = None
    available_days: list[str]
    slot_duration_minutes: int
    advance_booking_days: int
    active: bool


class Slot(BaseModel):
    slot_datetime: str
    available: bool
    duration_minutes: int
    slot_duration_minutes: int
    doctor_id: str
    doctor_name: str


class CreateAppointmentRequest(BaseModel):
    patient_id: str
    doctor_id: str
    slot_datetime: str
    specialty: str
    appointment_type: Literal["new", "follow_up"]
    slot_duration_minutes: Optional[int] = None
    specialty_notes: Optional[str] = ""
    linked_appointment_id: Optional[str] = None
    referral_confirmed: Optional[bool] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None

import re


def normalize_phone(phone: str) -> str | None:
    phone = phone.strip()
    if re.fullmatch(r"\+91\d{10}", phone):
        return phone
    if re.fullmatch(r"\d{10}", phone):
        return f"+91{phone}"
    return None

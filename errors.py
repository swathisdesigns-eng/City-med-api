from fastapi.responses import JSONResponse


def error_response(status_code: int, code: str, message: str, details: dict = {}):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}}
    )

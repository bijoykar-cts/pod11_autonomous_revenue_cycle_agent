def normalize_code(code: str) -> str:
    return code.strip().upper().replace(" ", "")


def normalize_code_system(code_system: str) -> str:
    value = code_system.strip().upper()
    if value in {"CM", "ICD10CM", "ICD-10CM"}:
        return "ICD-10-CM"
    if value in {"PCS", "ICD10PCS", "ICD-10PCS"}:
        return "ICD-10-PCS"
    return code_system.strip()

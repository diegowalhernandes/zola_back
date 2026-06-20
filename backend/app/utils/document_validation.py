"""Validação de documentos de identificação (CPF e passaporte)."""

from __future__ import annotations

import re

CPF_PATTERN = re.compile(r"^\d{11}$")
PASSPORT_PATTERN = re.compile(r"^[A-Z0-9]{6,20}$")

INVALID_CPFS = {
    "00000000000",
    "11111111111",
    "22222222222",
    "33333333333",
    "44444444444",
    "55555555555",
    "66666666666",
    "77777777777",
    "88888888888",
    "99999999999",
}


def normalize_document_number(document_type: str, value: str) -> str:
    cleaned = value.strip()
    if document_type == "cpf":
        return re.sub(r"\D", "", cleaned)
    return re.sub(r"[^A-Za-z0-9]", "", cleaned).upper()


def is_valid_cpf(value: str) -> bool:
    cpf = normalize_document_number("cpf", value)
    if not CPF_PATTERN.match(cpf) or cpf in INVALID_CPFS:
        return False

    digits = [int(char) for char in cpf]
    first_sum = sum(digit * weight for digit, weight in zip(digits[:9], range(10, 1, -1)))
    first_check = (first_sum * 10) % 11
    first_check = 0 if first_check == 10 else first_check
    if digits[9] != first_check:
        return False

    second_sum = sum(digit * weight for digit, weight in zip(digits[:10], range(11, 1, -1)))
    second_check = (second_sum * 10) % 11
    second_check = 0 if second_check == 10 else second_check
    return digits[10] == second_check


def is_valid_passport(value: str) -> bool:
    passport = normalize_document_number("passport", value)
    if not PASSPORT_PATTERN.match(passport):
        return False
    if passport.isdigit():
        return False
    return True


def validate_document(document_type: str, value: str) -> str:
    normalized_type = document_type.strip().lower()
    if normalized_type not in {"cpf", "passport"}:
        raise ValueError("Informe um tipo de documento válido: CPF ou passaporte.")

    normalized_number = normalize_document_number(normalized_type, value)
    if not normalized_number:
        raise ValueError("Informe o número do documento.")

    if normalized_type == "cpf":
        if not is_valid_cpf(normalized_number):
            raise ValueError("CPF inválido.")
        return normalized_number

    if not is_valid_passport(normalized_number):
        raise ValueError("Passaporte inválido.")
    return normalized_number

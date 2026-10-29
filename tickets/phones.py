import re


def normalize_phone(phone):
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10 and digits.startswith("9"):
        return "+7" + digits
    if len(digits) == 11 and digits[0] in "78":
        return "+7" + digits[1:]
    return ""

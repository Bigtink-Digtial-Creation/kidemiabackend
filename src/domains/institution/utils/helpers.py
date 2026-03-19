import re
import secrets
import string


def _generate_code(prefix: str, length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return f"{prefix}-{''.join(secrets.choice(chars) for _ in range(length))}"


def _random_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _generate_institution_code(name: str) -> str:
    """Derive a code from the name if the admin didn't supply one."""
    words = re.sub(r"[^a-zA-Z0-9 ]", "", name).split()
    acronym = "".join(w[0].upper() for w in words[:4])
    suffix = "".join(secrets.choice(string.digits) for _ in range(3))
    return f"{acronym}-{suffix}"

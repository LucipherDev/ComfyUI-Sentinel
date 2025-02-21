import re


def validate_username(username: str) -> tuple[bool, str]:
    """
    Validate username based on:
    - Only letters, numbers, and underscores.
    - No spaces.
    - At least 3 characters long.
    """
    if re.match(r"^[a-zA-Z0-9_]{3,}$", username):
        return True, ""
    return (
        False,
        "Username must be at least 3 characters, contain only letters, numbers, and underscores, and cannot contain spaces.",
    )


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password based on:
    - At least 8 characters long.
    - Must contain at least one digit.
    - Must contain at least one special character (e.g., !@#$%^&*).
    - Cannot contain spaces.
    """
    if re.match(r"^(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>?/`~])[A-Za-z\d!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>?/`~]{8,}$", password):
        return True, ""
    return (
        False,
        "Password must be at least 8 characters long, contain at least one digit, one special character, and no spaces.",
    )

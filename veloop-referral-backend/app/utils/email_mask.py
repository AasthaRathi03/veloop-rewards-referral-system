"""Email masking used only in security responses (self-referral modal)."""


def mask_email(email: str) -> str:
    """Mask the local part while preserving the domain.

    Rules (spec 35/36):
      * long local part  -> first 4 + *** + last 3      (ayanalam@x.com -> ayan***lam@x.com)
      * short local part -> first 2 + ***               (abc@gmail.com  -> ab***@gmail.com)
      * very short       -> first 1 + ***               (ab@gmail.com   -> a***@gmail.com)
    Never returns the complete local part.
    """
    if not email or "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        return f"{local[:1]}***@{domain}"
    if len(local) <= 7:
        return f"{local[:2]}***@{domain}"
    return f"{local[:4]}***{local[-3:]}@{domain}"

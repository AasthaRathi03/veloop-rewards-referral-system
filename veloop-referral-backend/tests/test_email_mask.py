from app.utils.email_mask import mask_email


def test_masking_rules():
    assert mask_email("ayanalam@example.com") == "ayan***lam@example.com"
    assert mask_email("abc@gmail.com") == "ab***@gmail.com"
    assert mask_email("ab@gmail.com") == "a***@gmail.com"
    assert mask_email("") == "***"


def test_never_reveals_full_local_part():
    for email in ("ayanalam@example.com", "abc@gmail.com", "verylonglocalpart@x.io"):
        local = email.split("@")[0]
        assert local not in mask_email(email)

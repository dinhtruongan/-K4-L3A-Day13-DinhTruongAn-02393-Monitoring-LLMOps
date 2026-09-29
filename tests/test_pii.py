from app.pii import scrub_text
from app.logging_config import scrub_event


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_vietnamese_identity_number() -> None:
    out = scrub_text("CCCD: 079123456789")
    assert "079123456789" not in out
    assert "REDACTED_CCCD" in out


def test_scrub_credit_card_formats() -> None:
    for card_number in ("4111 1111 1111 1111", "4111-1111-1111-1111", "4111111111111111"):
        out = scrub_text(f"Card: {card_number}")
        assert card_number not in out
        assert "REDACTED_CREDIT_CARD" in out


def test_log_processor_scrubs_nested_fields_before_rendering() -> None:
    event = {
        "event": "contact 0901234567",
        "payload": {"details": ["student@vinuni.edu.vn", {"id": "079123456789"}]},
    }

    scrubbed = scrub_event(None, "info", event)
    rendered = str(scrubbed)
    for raw_value in ("0901234567", "student@vinuni.edu.vn", "079123456789"):
        assert raw_value not in rendered

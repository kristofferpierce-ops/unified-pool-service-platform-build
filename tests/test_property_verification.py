from app.services.property_verification import evaluate_verification, person_name_match


def test_person_name_match_exact():
    assert person_name_match("John A. Smith", "Smith, John A")


def test_verified_owner_status():
    decision = evaluate_verification(
        caller_name="Jane Doe",
        caller_role="owner",
        input_address="123 Example St",
        owner_name="Jane Doe",
    )
    assert decision.status == "verified_owner"


def test_entity_likely_authorized_agent():
    decision = evaluate_verification(
        caller_name="Alex Manager",
        caller_role="property manager",
        input_address="123 Example St",
        owner_name="Sunset Holdings LLC",
        sunbiz_entity_name="Sunset Holdings LLC",
        sunbiz_role_matches="manager",
    )
    assert decision.status == "likely_authorized_agent"

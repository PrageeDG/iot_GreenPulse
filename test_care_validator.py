from validators.care_validator import (
    validate_care_response,
    CareValidationError,
)

valid_response = {
    "urgency": "LOW",
    "recommendation": "Do not water now. Recheck the soil later.",
    "watering_required": False,
    "reason": "Soil moisture is sufficient.",
    "literary_quote": "Nature does not hurry."
}

test_cases = [
    ("Valid response", valid_response, True),

    (
        "Missing recommendation",
        {
            key: value
            for key, value in valid_response.items()
            if key != "recommendation"
        },
        False,
    ),

    (
        "Invalid urgency",
        {**valid_response, "urgency": "EXTREME"},
        False,
    ),

    (
        "Incorrect Boolean type",
        {**valid_response, "watering_required": "true"},
        False,
    ),

    (
        "Empty recommendation",
        {**valid_response, "recommendation": ""},
        False,
    ),
]

for name, response, should_pass in test_cases:
    try:
        validate_care_response(response)
        passed = True
        message = "Accepted"
    except CareValidationError as error:
        passed = False
        message = str(error)

    result = "PASS" if passed == should_pass else "FAIL"
    print(f"{result}: {name} — {message}")
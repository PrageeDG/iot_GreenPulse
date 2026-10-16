class CareValidationError(Exception):
    """Raised when a Care Agent response fails validation."""


VALID_URGENCIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}


REQUIRED_FIELDS = {
    "urgency",
    "recommendation",
    "watering_required",
    "reason",
    "literary_quote",
}


def validate_care_response(
    response,
    env_data=None,
    weather_data=None,
):
    """
    Validate a Care Agent response before MQTT publication.

    Returns a validated copy of the response.
    Raises CareValidationError if validation fails.
    """

    if not isinstance(response, dict):
        raise CareValidationError(
            "Care response must be a dictionary."
        )

    # 1. Validate required fields.
    missing_fields = REQUIRED_FIELDS - response.keys()

    if missing_fields:
        raise CareValidationError(
            f"Missing fields: {sorted(missing_fields)}"
        )

    validated = dict(response)

    # 2. Validate urgency.
    urgency = response["urgency"]

    if not isinstance(urgency, str):
        raise CareValidationError(
            "Urgency must be a string."
        )

    urgency = urgency.strip().upper()

    if urgency not in VALID_URGENCIES:
        raise CareValidationError(
            f"Invalid urgency: {urgency}"
        )

    validated["urgency"] = urgency

    # 3. Validate required text fields.
    for field in (
        "recommendation",
        "reason",
        "literary_quote",
    ):
        value = response[field]

        if not isinstance(value, str) or not value.strip():
            raise CareValidationError(
                f"{field} must be a non-empty string."
            )

        if len(value) > 2000:
            raise CareValidationError(
                f"{field} exceeds the maximum length."
            )

        validated[field] = value.strip()

    # 4. Validate Boolean type strictly.
    if not isinstance(response["watering_required"], bool):
        raise CareValidationError(
            "watering_required must be a Boolean."
        )

    # 5. Check for major urgency disagreement.
    env_data = env_data or {}

    soil_urgency = env_data.get("soil_urgency")

    if isinstance(soil_urgency, str):
        soil_urgency = soil_urgency.strip().upper()

        if soil_urgency in VALID_URGENCIES:
            urgency_rank = {
                "LOW": 1,
                "MEDIUM": 2,
                "HIGH": 3,
                "CRITICAL": 4,
            }

            difference = abs(
                urgency_rank[urgency]
                - urgency_rank[soil_urgency]
            )

            if difference >= 2:
                raise CareValidationError(
                    "Care urgency differs significantly "
                    "from the environmental assessment."
                )

    # 6. Check watering advice against known conditions.
    weather_data = weather_data or {}

    rain_expected = weather_data.get("rain_expected")

    soil_moisture = env_data.get("soil_moisture")

    if soil_moisture is None:
        soil_moisture = env_data.get(
            "current_soil_moisture"
        )

    try:
        soil_moisture = (
            float(soil_moisture)
            if soil_moisture is not None
            else None
        )
    except (TypeError, ValueError):
        soil_moisture = None

    if (
        validated["watering_required"]
        and rain_expected is True
        and soil_moisture is not None
        and soil_moisture >= 70
    ):
        raise CareValidationError(
            "Watering recommendation requires review: "
            "rain is expected and soil moisture is high."
        )

    return validated


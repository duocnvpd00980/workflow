from pydantic import BaseModel


class ShieldSpec(BaseModel):

    shield_name: str

    version: str = "v1"

    stable: bool = True

    telemetry_enabled: bool = True


SHIELD_REGISTRY = {

    "AGENT_ADS": ShieldSpec(
        shield_name="AGENT_ADS"
    ),

    "AGENT_EMAIL": ShieldSpec(
        shield_name="AGENT_EMAIL"
    ),
}
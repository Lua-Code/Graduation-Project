from dataclasses import dataclass

from drsim.shared.enums import VictimHealth, VictimStatus


@dataclass
class VictimState:
    id: str
    incident_id: str
    health: VictimHealth  # placeholder rules; KAN-4 owns the real ones
    status: VictimStatus = VictimStatus.TRAPPED
    health_points: float = 100.0  # placeholder; KAN-4 owns the real rules

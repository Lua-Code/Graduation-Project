from dataclasses import dataclass, field

from drsim.shared.enums import IncidentStatus, IncidentType


@dataclass
class IncidentState:
    id: str
    type: IncidentType
    node_id: str
    priority: int  # 1 to 5, 5 is highest priority
    status: IncidentStatus = IncidentStatus.OPEN
    victim_ids: list[str] = field(default_factory=list)

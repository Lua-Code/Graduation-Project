from dataclasses import dataclass

from drsim.shared.enums import UnitStatus, UnitType


@dataclass
class UnitState:
    id: str
    type: UnitType
    node_id: str
    status: UnitStatus = UnitStatus.AVAILABLE
    assigned_incident_id: str | None = None

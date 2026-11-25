from dataclasses import dataclass, replace

from drsim.shared.enums import EdgeState, UnitCapability, UnitStatus, UnitType
from drsim.shared.schemas import DEFAULT_DEGRADED_TRAVEL_MULTIPLIER, MapEdge
from drsim.simulation.world.graph import edge_travel_ticks

DEFAULT_CAPABILITIES = {
    UnitType.RESCUE: (UnitCapability.RESCUE,),
    UnitType.AMBULANCE: (UnitCapability.TRANSPORT,),
    UnitType.FIRE: (),
}

_TRAVELLING = (UnitStatus.EN_ROUTE, UnitStatus.TRANSPORTING, UnitStatus.RETURNING)
_TRANSITIONS = {
    UnitStatus.AVAILABLE: (UnitStatus.EN_ROUTE, UnitStatus.UNAVAILABLE),
    UnitStatus.EN_ROUTE: (UnitStatus.ON_SCENE, UnitStatus.AVAILABLE),
    UnitStatus.ON_SCENE: (UnitStatus.TRANSPORTING, UnitStatus.RETURNING, UnitStatus.AVAILABLE),
    UnitStatus.TRANSPORTING: (UnitStatus.RETURNING, UnitStatus.AVAILABLE),
    UnitStatus.RETURNING: (UnitStatus.AVAILABLE,),
    UnitStatus.UNAVAILABLE: (UnitStatus.AVAILABLE,),
}


def can_dispatch_transition(current_status: UnitStatus, next_status: UnitStatus) -> bool:
    return next_status in _TRANSITIONS[current_status]


@dataclass(frozen=True)
class EdgeTraversal:
    edge_id: str
    destination: str
    duration_ticks: int
    elapsed_ticks: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.elapsed_ticks < self.duration_ticks:
            raise ValueError("Invalid edge traversal progress")


@dataclass(frozen=True)
class UnitState:
    """Engine-owned value. node_id always identifies the last reached road node."""

    id: str
    type: UnitType
    node_id: str
    status: UnitStatus = UnitStatus.AVAILABLE
    assigned_incident_id: str | None = None
    capabilities: tuple[UnitCapability, ...] | None = None
    available_from_tick: int = 0
    movement: EdgeTraversal | None = None

    def __post_init__(self) -> None:
        if self.capabilities is None:
            object.__setattr__(self, "capabilities", DEFAULT_CAPABILITIES[self.type])
        if self.available_from_tick < 0:
            raise ValueError("Availability tick must be nonnegative")
        if self.movement and self.status not in _TRAVELLING:
            raise ValueError("Only travelling units can occupy a road edge")

    def is_available(self, tick: int, capability: UnitCapability | None = None) -> bool:
        return (
            self.status == UnitStatus.AVAILABLE
            and self.assigned_incident_id is None
            and self.movement is None
            and tick >= self.available_from_tick
            and (capability is None or capability in (self.capabilities or ()))
        )

    def transition(
        self, target: UnitStatus, *, tick: int, incident_id: str | None = None
    ) -> "UnitState":
        if not can_dispatch_transition(self.status, target):
            raise ValueError(f"Invalid unit transition: {self.status} -> {target}")
        assignment = self.assigned_incident_id
        if target == UnitStatus.EN_ROUTE:
            if not incident_id or not self.is_available(tick):
                raise ValueError("Dispatch requires an available unit and an incident")
            assignment = incident_id
        elif incident_id is not None:
            raise ValueError("Only dispatch accepts a new incident")
        if target == UnitStatus.TRANSPORTING and UnitCapability.TRANSPORT not in (
            self.capabilities or ()
        ):
            raise ValueError("Transport capability required")
        if self.movement and target != UnitStatus.AVAILABLE:
            raise ValueError("Complete the current edge before changing status")
        if target in (UnitStatus.AVAILABLE, UnitStatus.RETURNING, UnitStatus.UNAVAILABLE):
            assignment = None
        return replace(self, status=target, assigned_incident_id=assignment, movement=None)

    def enter_edge(
        self,
        edge: MapEdge,
        state: EdgeState,
        tick_seconds: int,
        *,
        degraded_multiplier: float = DEFAULT_DEGRADED_TRAVEL_MULTIPLIER,
    ) -> "UnitState":
        if self.movement or self.status not in _TRAVELLING:
            raise ValueError("Unit must be travelling and at a node to enter an edge")
        if self.node_id == edge.sourceNodeId:
            destination = edge.targetNodeId
        elif edge.bidirectional and self.node_id == edge.targetNodeId:
            destination = edge.sourceNodeId
        else:
            raise ValueError("Edge cannot be entered from the current node")
        duration = edge_travel_ticks(
            edge, state, tick_seconds, degraded_multiplier=degraded_multiplier
        )
        if duration is None:
            raise ValueError("Cannot enter a blocked edge")
        return replace(self, movement=EdgeTraversal(edge.edgeId, destination, duration))

    def advance_movement(self) -> "UnitState":
        """Advance one simulated tick. The engine decides when to enter the next edge."""
        move = self.movement
        if move is None:
            return self
        elapsed = move.elapsed_ticks + 1
        if elapsed == move.duration_ticks:
            return replace(self, node_id=move.destination, movement=None)
        return replace(self, movement=replace(move, elapsed_ticks=elapsed))

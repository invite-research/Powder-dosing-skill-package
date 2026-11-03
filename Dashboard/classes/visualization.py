from dataclasses import dataclass,field
from typing import Any, Optional, List


@dataclass
class CurrentSession:

    # Session 
    session_state: str = "IDLE"
    dosing_mode: str = "NORMAL"
    controller_name: str = "CLASSIC"

    # Live dosing 
    latest_weight: float = 0.0
    target_weight: float = 0.0
    remaining_weight: float = 0.0

    # Powder 
    powder_id: int = 0
    powder_name: str = "UNKNOWN"

    # Container 
    container_id: int = 0
    container_shape: str = "UNKNOWN"
    container_level: float = 0.0

    container_height_mm: float = 0.0
    container_mouth_d_mm: float = 0.0
    container_mouth_sh_mm: float = 0.0
    container_length_mm: float = 0.0
    container_diameter_mm: float = 0.0
    container_empty_weight_g: float = 0.0
    container_volume_ml: float = 0.0

    # Tool 
    spatula_type: str = "N/A"
    spatula_target_qty: float = 0.0

    # Datacode 
    latest_datacode_raw: str = ""
    latest_container_id: int = 0
    latest_powder_id: int = 0

    final_weight: float = 0.0
    absolute_error: float = 0.0
    completion_percent: float = 0.0
    scoop_count: int = 0
    scoop_start_weight: float = 0.0
    active_scoop_spatula: str = ""
    active_scoop_target: float = 0.0
    scoop_results: List[dict[str, Any]] = field(default_factory=list)
    
    def update_remaining(self):

        self.remaining_weight = max(
            self.target_weight-self.latest_weight,
            0.0
        )
        
@dataclass
class RecipeState:

    powder_labels: List[str] = field(
        default_factory=lambda: ["Powder A","Powder B","Powder C"]
    )

    current_slot_index: Optional[int] = None

    init_total: float = 0.0
    init_percent: List[float] = field(default_factory=lambda:[0.0,0.0,0.0])
    init_weight: List[float] = field(default_factory=lambda:[0.0,0.0,0.0])

    final_total: float = 0.0
    final_percent: List[float] = field(default_factory=lambda:[0.0,0.0,0.0])
    final_weight: List[float] = field(default_factory=lambda:[0.0,0.0,0.0])

    percent_error: List[float] = field(default_factory=lambda:[0.0,0.0,0.0])

    slot_powder: List[str] = field(default_factory=lambda:["N/A","N/A","N/A"])
    slot_target: List[float] = field(default_factory=lambda:[0.0,0.0,0.0])
    slot_spatula: List[str] = field(default_factory=lambda:["N/A","N/A","N/A"])
    slot_scoop_target: List[float] = field(default_factory=lambda:[0.0,0.0,0.0])
    slot_level: List[float] = field(default_factory=lambda:[0.0,0.0,0.0])

    def find_slot_index(self, powder_name_raw: str):

        powder_name_upper = powder_name_raw.strip().upper()

        for i,label in enumerate(self.powder_labels):

            if powder_name_upper == label.strip().upper():
                return i

        return None

    def slot_from_query(self, powder_slot):

        if not powder_slot:
            return None

        s = powder_slot.upper()

        if s in ("A","1","POWDER_A"):
            return 0

        if s in ("B","2","POWDER_B"):
            return 1

        if s in ("C","3","POWDER_C"):
            return 2

        return None

@dataclass
class VisualizationState:

    current_session: CurrentSession = field(default_factory=CurrentSession)

    recipe: RecipeState = field(default_factory=RecipeState)

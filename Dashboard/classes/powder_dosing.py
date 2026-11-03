
import time
import numpy as np
from classes.labdatabase import LabDatabase
from classes.scaledevice import WeighScale
from classes.scaledevice import PCEScale
from classes.tilting_station import POTS
from classes.datacode_reader import DatacodeReader

class Dosing:
    
    def __init__(self, db: LabDatabase, 
                 scale: WeighScale,
                 scale2: PCEScale,
                 datacodereader: DatacodeReader,
                 tiltstation: POTS
                 ):
        self.db = db
        self.scale = scale
        self.scale2 = scale2
        self.tiltstation = tiltstation
        self.datacodereader = datacodereader
        self.pow_name: str = "N/A"
        self.target_weight: float = 0.0 
        self.current_container_weight: float = 0.0
        self.last_scale: float = 0.0
        self.timeout = 5
        self.hinge_offset: float = 5
    
    '''
    def find_powder_in_registy(self, pow_name) -> str:
        if pow_name is None:
            raise ValueError("powder_id cannot be None")
        
        powder_id = self.db.fetch_powder_id_by_name(pow_name)
        rows = self.db.fetch_id_by_powder(powder_id)

        if not rows:
            raise ValueError(f"No datacode entries found for powder_id: {pow_name}")
        result = []
        for row in rows:
            datacode_code = row.get("datacode_id")

            if not datacode_code or not re.fullmatch(r"code\d{3}", datacode_code):
                continue
            result.append({"code_ids: ", datacode_code})
            
        return result
    '''
    
    def compute_level_percent(self, powder_id: str, container_id:str)-> float:
        
        try: 
            weight_full = self.datacodereader.compute_weight_full(powder_id)
            weight_empty = self.datacodereader.compute_weight_empty(container_id)
            start = time.time()
            curr_weight = self.current_container_weight
            
            # wait for robot to place the container on top of PCE weigh scale
            while curr_weight == 0.0:
                curr_weight = self.current_container_weight
                if curr_weight != 0.0:
                    return curr_weight
            
                if time.time() - start > self.timeout:
                    raise TimeoutError("Value stayed zero for 5 seconds")
                
                time.sleep(0.1)
                
            dosed_weight = self.scale.read_weight()
            
            delta = dosed_weight - self.last_scale
            if (delta<0.0):
                delta = 0.0
            
            w_dosed_total = w_dosed_total + delta
            self.last_scale = dosed_weight
            
            W_eff = curr_weight-w_dosed_total
            if (W_eff<weight_empty):
                W_eff = weight_empty
            
            
            # Compute powder level %
            level = 100.0* (W_eff -weight_empty)/ (weight_full-weight_empty)
            
            # Clamp to 0–100
            level = np.clip(level,0.0,100.0)

            return level
        except Exception as e:
            print(f"[ERROR] {e}")
            return None
    
    def compute_scoop_depth(self)-> float:
        try:

            cum_w = self.scale.read_weight()
        except Exception as e:
            print(f"[ERROR] {e}")
            return None
        

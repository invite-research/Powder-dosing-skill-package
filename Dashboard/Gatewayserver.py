import socket
import time
import traceback
# DATA VISUALIZATION STATE 
from classes.visualization import VisualizationState
from classes.weightlogger import WeightLogger

# DATACODE READING STATE 
from classes.datacode_reader import DatacodeReader

# DEVICES 
from classes.scaledevice import WeighScale
from classes.scaledevice import PCEScale
from classes.tilting_station import POTS

# DATABASES 
from classes.labdatabase import LabDatabase

# DOSING STATE 
from classes.powder_dosing import Dosing

#Swab Test Path Generator
#from classes.Crisscrosspath import ZigzagWaypointGenerator


# GATEWAY / COMMANDS 
class GatewayServer():
    def __init__(self, host: str, port: int, scale: WeighScale, scale2:PCEScale, db: LabDatabase, pots:POTS, visualizer: VisualizationState, logger: WeightLogger, datacode_reader: DatacodeReader, dosing: Dosing, 
                 #generator: ZigzagWaypointGenerator
                 ):
        super().__init__
        self.host = host
        self.port = port
        self.scale = scale
        self.scale2 = scale2
        self.db = db
        self.pots = pots
        self.visualizer = visualizer
        self.logger = logger
        self.datacode_reader = datacode_reader
        self.dosing = dosing
        #self.generator = generator #Alphin

    def get_weight_response(self) -> str:
        s = self.visualizer.current_session
        try:
            weight = self.scale.read_weight()

            s.latest_weight = weight

            if s.session_state == "ERROR":
                s.session_state = "DOSING" if s.target_weight > 0.0 else "IDLE"

            if s.session_state == "READY":
                s.session_state = "DOSING"

            s.update_remaining()
            s.remaining_weight = max(
                s.target_weight - weight,
                0.0
            )
            if s.remaining_weight == 0.0 and s.session_state == "DOSING":
                
                s.final_weight = s.latest_weight
                s.absolute_error = s.final_weight - s.target_weight
                if s.target_weight > 0:
                    s.completion_percent = (
                        s.final_weight / s.target_weight
                    ) * 100
                else:
                    s.completion_percent = 0.0
                self._complete_active_scoop(s, s.final_weight)
                s.session_state = "FINISHED"
                self._export_validation_log(s)

            self.logger.append_live_weight(
                self.visualizer.recipe.current_slot_index,
                weight,
                s.spatula_type
            )
            print(f"[TCP] get_weight: {weight}")
            return f"({weight:.3f})\n"
        except Exception as e:
            print(f"[ERROR] get_weight: {e}")
            if s is not None:
                s.session_state = "ERROR"
            return "(0.000)\n"

    def tare_response(self) -> str:
        try:
            return "(TARED)\n" if self.scale.tare() else "(FAILED)\n"
        except Exception as e:
            print(f"Error sending tare: {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(FAILED)\n"

    def zero_response(self) -> str:
        try:
            return "(ZEROED)\n" if self.scale.zero() else "(FAILED)\n"
        except Exception as e:
            print(f"Error sending zero: {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(FAILED)\n"

    def _set_target(self, cmd: str) -> str:

        try:

            target = float(cmd.split(":", 1)[1].strip())

            self.visualizer.current_session.target_weight = target
            self.visualizer.current_session.scoop_count = 0
            self.visualizer.current_session.scoop_start_weight = 0.0
            self.visualizer.current_session.active_scoop_spatula = ""
            self.visualizer.current_session.active_scoop_target = 0.0
            self.visualizer.current_session.scoop_results.clear()

            if self.visualizer.recipe.current_slot_index is not None:

                self.visualizer.recipe.slot_target[
                    self.visualizer.recipe.current_slot_index
                ] = self.visualizer.current_session.target_weight

            # Start a new logging session
            self.logger.start_new_session(
                self.visualizer.recipe.current_slot_index
            )
            
            self.visualizer.current_session.session_state = "READY"
            return "(TARGET_OK)\n"

        except Exception as e:

            print(f"[ERROR] SET_TARGET failed: {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(TARGET_ERROR)\n"
        
    def _set_powder(self, data: str) -> str:

        try:

            powder_name_raw = data.split(":",1)[1].strip().upper()

            self.visualizer.current_session.powder_name = powder_name_raw.upper()
            powder_id = self.db.fetch_powder_id_by_name(powder_name_raw)
            if powder_id is not None:
                self.visualizer.current_session.powder_id = int(powder_id)

            self.visualizer.recipe.current_slot_index = \
                self.visualizer.recipe.find_slot_index(powder_name_raw)

            print(
                f"[TCP] Active powder → "
                f"{powder_name_raw}"
            )

        except Exception as e:

            print(e)
    
            self.visualizer.current_session.session_state = "ERROR"
            return "(POWDER_ERROR)\n"

        if self.visualizer.recipe.current_slot_index is not None:

            self.visualizer.recipe.slot_powder[
                self.visualizer.recipe.current_slot_index
            ] = powder_name_raw

        return "(POWDER_OK)\n"

    def _set_spatula(self, cmd: str) -> str:
        try:
            session = self.visualizer.current_session
            print(f"[SPATULA] command={cmd!r}, powder_name={session.powder_name!r}")
            self._complete_active_scoop(session, session.latest_weight)

            session.spatula_type = cmd.split(":", 1)[1].strip().upper()
            #print(f"[TCP] Spatula type set → {session.spatula_type}")

            #spatula_name = cmd.split(":", 1)[1].strip()
            #print(f"[TCP] Spatula name: {spatula_name}")
            spatula_id = self.db.fetch_spatula_by_name(session.spatula_type)

            spatula_row = self.db.fetch_spatula_by_id(spatula_id) if spatula_id is not None else None
            #print(f"[TCP] Spatula row: {spatula_row}")
            spatula_volume = spatula_row["volumes_ml"] if spatula_row is not None else 0.0
            #print(f"[TCP] Spatula volume: {spatula_volume} mL")
            powder = self.db.fetch_powder_id_by_name(session.powder_name)
            #print(f"[TCP] Powder ID: {powder}")
            powder_row = self.db.fetch_powder_by_id(powder) if powder is not None else None
            if powder is None or powder_row is None:
                print(
                    f"[SPATULA] Powder lookup failed for "
                    f"{session.powder_name!r}; using density 0.0"
                )
            #print(f"[TCP] Powder Row: {powder_row}")
            powder_density = powder_row["bulk_density"] if powder_row is not None else 0.0
            #print(f"[TCP] Spatula volume: {spatula_volume} mL, Powder density: {powder_density} g/mL")
            target_mass = spatula_volume * powder_density
            session.spatula_target_qty = target_mass
            #print(f"[TCP] Spatula target mass: {target_mass:.3f} g")
            if session.session_state in ("READY", "DOSING"):
                session.active_scoop_spatula = session.spatula_type
                session.active_scoop_target = target_mass
                session.scoop_start_weight = session.latest_weight
            #print(f"[TCP] Spatula type set → {self.visualizer.current_session.spatula_type} (target mass: {target_mass:.3f} g)")

            return "(SPATULA_OK)\n"
        except Exception as e:
            print(f"[ERROR] SET_Spatula parse failed for {cmd!r}: {e!r}")
            traceback.print_exc()
            self.visualizer.current_session.session_state = "ERROR"
            return "(Spatula_ERROR)\n"
        
    def _set_level(self, cmd: str) -> str:
        try:
            level = float(cmd.split(":", 1)[1])
            self.visualizer.current_session.container_level = level
            # The robot sends SET_LEVEL once as it starts each scoop cycle.
            if self.visualizer.current_session.session_state in ("READY", "DOSING"):
                self.visualizer.current_session.scoop_count += 1
            if self.visualizer.recipe.current_slot_index is not None:
                self.visualizer.recipe.slot_level[self.visualizer.recipe.current_slot_index] = level
            print(f"[TCP] Container level updated → {level:.2f}% (slot {self.visualizer.recipe.current_slot_index})")
            return "(LEVEL_OK)\n"
        except Exception as e:
            print(f"[ERROR] SET_LEVEL parse failed: {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(LEVEL_ERROR)\n"

    def _set_labels(self, data: str) -> str:
        try:
            _, payload = data.split(":", 1)
            parts = [p.strip() for p in payload.split(";")]
            for i in range(min(3, len(parts))):
                if parts[i]:
                    self.visualizer.recipe.powder_labels[i] = parts[i]
            print(f"[TCP] Powder labels updated → {self.visualizer.recipe.powder_labels}")
            return "(LABELS_OK)\n"
        except Exception as e:
            print(f"[ERROR] SET_LABELS parse failed: {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(LABELS_ERROR)\n"

    def _set_init(self, data: str) -> str:
        try:
            _, payload = data.split(":", 1)
            fields = [f.strip() for f in payload.split(";")]
            if len(fields) < 4:
                raise ValueError("need TOTAL;PA;PB;PC")

            self.visualizer.recipe.init_total = float(fields[0])
            self.visualizer.recipe.init_percent = [float(fields[1]), float(fields[2]), float(fields[3])]
            self.visualizer.recipe.init_weight = [
                self.visualizer.recipe.init_total * self.visualizer.recipe.init_percent[0] / 100.0,
                self.visualizer.recipe.init_total * self.visualizer.recipe.init_percent[1] / 100.0,
                self.visualizer.recipe.init_total * self.visualizer.recipe.init_percent[2] / 100.0,
            ]
            print(f"[TCP] Init recipe set: total={self.visualizer.recipe.init_total}, perc={self.visualizer.recipe.init_percent}")
            return "(INIT_OK)\n"
        except Exception as e:
            print(f"[ERROR] SET_INIT parse failed: {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(INIT_ERROR)\n"

    def _set_final(self, data: str) -> str:
        try:
            _, payload = data.split(":", 1)
            fields = [f.strip() for f in payload.split(";")]
            if len(fields) < 7:
                raise ValueError("need ADJ_TOTAL;PA;PB;PC;WA;WB;WC")

            self.visualizer.recipe.final_total = float(fields[0])
            self.visualizer.recipe.final_percent = [float(fields[1]), float(fields[2]), float(fields[3])]
            self.visualizer.recipe.final_weight = [float(fields[4]), float(fields[5]), float(fields[6])]
            self.visualizer.recipe.percent_error = [
                self.visualizer.recipe.final_percent[0] - self.visualizer.recipe.init_percent[0],
                self.visualizer.recipe.final_percent[1] - self.visualizer.recipe.init_percent[1],
                self.visualizer.recipe.final_percent[2] - self.visualizer.recipe.init_percent[2],
            ]
            print(
                f"[TCP] Final recipe set: total={self.visualizer.recipe.final_total}, "
                f"perc={self.visualizer.recipe.final_percent}, w={self.visualizer.recipe.final_weight}, err={self.visualizer.recipe.percent_error}"
            )
            return "(FINAL_OK)\n"
        except Exception as e:
            print(f"[ERROR] SET_FINAL parse failed: {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(FINAL_ERROR)\n"

    def _scan_datacode(self, data: str) -> str:
        try:
            result = self.datacode_reader.compute_weight_full(2,101)
            print(f"[datacode] scan result: {result}")
            return "(datacode_OK)\n"
        except Exception as e:
            print(f"[datacode] SCAN_datacode error: {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(datacode_ERROR)\n"
        
    # #reading POTS Target Marker - Owner Alphin
    # def _scan_target_marker(self, data: str) -> str:
    #     try:
    #         result = self.datacode_reader.scan_raw()
    #         self.generator.target_pose_reader(result)
    #         print(f"[POTS] Target marker scan result: {result}")
    #         return "(TARGET_MARKER_OK)\n"
    #     except Exception as e:
    #         print(f"[POTS] SCAN_target_marker error: {e}")
    #         self.visualizer.current_session.session_state = "ERROR"
    #         return "(TARGET_MARKER_ERROR)\n"

    def _get_datacode_floats(self, data: str) -> str:
        try:
            s = self.datacode_reader.scan_and_resolve()
            session = self.visualizer.current_session
            session.container_id = int(s["container_id"])
            session.powder_id = int(s["powder_id"])
            session.powder_name = str(s["powder_name"]).upper()
            shape_code = 1.0 if s['shape'] == "CYLINDRICAL" else 0.0
            
            if s['flowability'] == "MEDIUM": 
                flow_code = 1.0 
            elif s['flowability'] == "LOW":
                flow_code = 2.0 
            else: 
                flow_code = 0.0
                
            return (
                f"({float(s['container_id']):g} , "
                f"{float(s['powder_id']):g} , "
                f"{float(s['bulk_density']):g} , "
                f"{float(s['height_mm']):g} , "
                f"{float(s['height_c_mm']):g} , "
                f"{float(s['mouth_d_mm']):g} , "
                f"{float(s['mouth_sh_mm']):g} , "
                f"{float(s['length_mm']):g} , "
                f"{float(s['diameter_mm']):g} , "
                f"{float(s['empty_weight_g']):g} , "
                f"{float(s['volume_ml']):g} , " 
                f"{float(s['full_weight_g']):g} , "
                f"{flow_code:g} , "
                f"{shape_code:g} )\n"
        )
        except Exception as e:
                print(f"[datacode] GET_datacode_FLOATS error: {e}")
                self.visualizer.current_session.session_state = "ERROR"
                return "ERR\n"

    def _get_spatula_floats(self, data: str) -> str:
        try:
            values = []
            for spatula in self.db.fetch_all_spatulas():
                values.extend([
                    float(spatula["sdepth_mm"]),
                    float(spatula["slength_mm"]),
                    float(spatula["volumes_ml"]),
                    float(spatula["retention_default_theta"]),
                    float(spatula["spatula_length_mm"]),
                ])
            return "(" + " , ".join(f"{value:g}" for value in values) + ")\n"
        except Exception as e:
            print(f"[spatula] GET_SPATULA_FLOATS error: {e}")
            return "ERR\n"

    def _export_validation_log(self, session) -> None:
        """Export the final validation values once a dosing session finishes."""

        powder = None
        if session.powder_id:
            powder = self.db.fetch_powder_by_id(session.powder_id)
        if powder is None and session.powder_name:
            powder_id = self.db.fetch_powder_id_by_name(session.powder_name)
            powder = self.db.fetch_powder_by_id(powder_id) if powder_id is not None else None

        validation_log_path = self.logger.export_validation_log(
            container_id=session.container_id,
            powder_flowability=(powder["flowability"] if powder else "UNKNOWN"),
            powder_id=session.powder_id or None,
            powder_level=session.container_level,
            target_weight=session.target_weight,
            dosed_weight=session.final_weight,
            number_of_scoops=len(session.scoop_results) or session.scoop_count,
        )

        live_log_path = self.logger.get_log_path(self.visualizer.recipe.current_slot_index)
        session_snapshot = {
            "state": session.session_state,
            "controller_name": session.controller_name,
            "powder_name": session.powder_name,
            "powder_id": session.powder_id,
            "container_id": session.container_id,
            "container_level": session.container_level,
            "target_weight": session.target_weight,
            "final_weight": session.final_weight,
            "absolute_error": session.absolute_error,
            "completion_percent": session.completion_percent,
            "spatula_type": session.spatula_type,
            "scoop_count": session.scoop_count,
        }

        try:
            self.logger.export_dashboard_bundle(
                live_log_path=live_log_path,
                session_snapshot=session_snapshot,
                scoop_results=list(session.scoop_results),
                validation_log_path=validation_log_path,
            )
        except Exception as exc:
            print(f"[VALIDATION] Dashboard export failed: {exc}")

    @staticmethod
    def _complete_active_scoop(session, ending_weight: float) -> None:
        """Store one scoop result from the cumulative dispensing-scale weight."""

        if not session.active_scoop_spatula or session.active_scoop_target <= 0.0:
            return

        actual_dosed = max(ending_weight - session.scoop_start_weight, 0.0)
        session.scoop_results.append(
            {
                "scoop_number": len(session.scoop_results) + 1,
                "spatula": session.active_scoop_spatula,
                "scoop_target": session.active_scoop_target,
                "actual_dosed": actual_dosed,
            }
        )
        session.active_scoop_spatula = ""
        session.active_scoop_target = 0.0
   
    def _ugo_dosing_info(self, data: str) -> str:
        try:
            _, ugo = data.split(":", 1)
            field = [f.strip() for f in ugo.split(";")]
            
            if len(field) != 2:
                raise ValueError(f"Invalid message format: {data}")
           
            powder_name = field[0]
            target_weight = float(field[1])

            #powder_id = self.db.fetch_powder_id_by_name(powder_name)

            #if powder_id is None:
            #    raise ValueError(f"powder not found: {powder_name}")

            self.dosing.pow_name = powder_name
            self.dosing.target_weight = target_weight

            print(f"[TCP] Target Powder: {powder_name}")
            print(f"[TCP] Target Amount: {target_weight}")
            #print(f"[TCP] powder_id: {powder_id}")

            return "(SET_powder OK)\n"
        
        except Exception as e:
            print(f"[ERROR] Target Powder can't find: {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(SET_powder error)\n"

    def _pots_home(self) -> str:
        try:
            result = self.pots.pots_home()
            if result != "[PoTS] OK\n":
                raise RuntimeError(result.strip())
            
            return ("(pots pose OK)\n")
        except Exception as e:
            print(f"[ERROR] bad cmd {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(pots_home error)\n"
    
    def _pots_tilt(self, cmd: str) -> str:
        try:
            val = float(cmd.split(":", 1)[1])
            self.pots.pots_tilt(val)
            
            return ("(pots tilt OK)\n")
        except Exception as e:
            print(f"[ERROR] bad cmd {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(pots_tilt error)\n"
        
    def _pots_fullrotate(self, cmd: int) -> str:
        try:
            val = float(cmd.split(":", 1)[1])
            self.pots.pots_fullrotate(val)
            
            return ("(pots fullrotate OK)\n")
        except Exception as e:
            print(f"[ERROR] bad cmd {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(pots_fullrotate error)\n"
        
    def _pots_CCWrotate(self, cmd: str) -> str:
        try:
            val = float(cmd.split(":", 1)[1])
            self.pots.pots_CCWrotate(val)
            
            return ("(pots CCWrotate OK)\n")
        except Exception as e:
            print(f"[ERROR] bad cmd {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(pots_CCWrotate error)\n"

    def _pots_CWrotate(self, cmd: str) -> str:
        try:
            val = float(cmd.split(":", 1)[1])
            self.pots.pots_CWrotate(val)
            
            return ("(pots CWrotate OK)\n")
        except Exception as e:
            print(f"[ERROR] bad cmd {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(pots_CWrotate error)\n"

    def _read_container_weight(self) -> str:
        try:
            #weight = self.scale2.read_weight_once()
            #self.scale2.tare()
            #time.sleep(2)
            weight = self.scale2.get_cont_weight()
            self.dosing.current_container_weight = weight
            print(f"current container weight: {weight}")
            return f"({weight:.3f})\n"
        except Exception as e:
            print(f"[ERROR] get_weight: {e}")
            self.visualizer.current_session.session_state = "ERROR"
            return "(0.000)\n"

    def handle_command(self, data: str) -> str:
        cmd = data.upper()

        if cmd == "GET_WEIGHT":
            return self.get_weight_response()
        if data == "TARE":
            return self.tare_response()
        if data == "ZERO":
            return self.zero_response()
        if cmd == "GET_CONT_WEIGHT":
            return self._read_container_weight()
        if cmd.startswith("SET_TARGET:"):
            return self._set_target(cmd)
        if cmd.startswith("SET_POWDER:"):
            return self._set_powder(data)
        if cmd.startswith("SET_SPATULA:"):
            return self._set_spatula(cmd)
        if cmd.startswith("SET_LEVEL:"):
            return self._set_level(cmd)
        if cmd.startswith("SET_LABELS:"):
            return self._set_labels(data)
        if cmd.startswith("SET_INIT:"):
            return self._set_init(data)
        if cmd.startswith("SET_FINAL:"):
            return self._set_final(data)
        if cmd.startswith("PICK:"):
            return self._ugo_dosing_info(data)
        if cmd.startswith("HOME"):
            return self._pots_home()
        if cmd.startswith("TILT:"):
            return self._pots_tilt(cmd)
        if cmd.startswith("FULLROTATE:"):
            return self._pots_fullrotate(cmd)
        if cmd.startswith("CCWROTATE:"):
            return self._pots_CCWrotate(cmd)
        if cmd.startswith("CWROTATE:"):
            return self._pots_CWrotate(cmd)
        if cmd.startswith("SCAN"):
            return self._scan_datacode(data)
        if cmd.startswith("GET_DATACODE_FLOATS"):
            return self._get_datacode_floats(data)
        if cmd.startswith("GET_SPATULA_FLOATS"):
            return self._get_spatula_floats(data)
        # if cmd.startswith("SCAN_TARGET_MARKER"): #Alphin
        #     return self._scan_target_marker(data)
        return "(INVALID_CMD)"

    def run(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(5)
        print(f"[TCP SERVER] Listening on port {self.port}…")
        print(f"System is running on: http://127.0.0.1:5000")


        while True:
            c, _ = srv.accept()
            try:
                raw_data = c.recv(1024)
                print(f"[TCP RAW RX] {raw_data!r}")
                data = raw_data.decode().strip()
                if not data:
                    continue
                print(f"[TCP] {data!r}")
                resp = self.handle_command(data)
                raw_response = resp.encode("ascii")
                print(f"[TCP RAW TX] {raw_response!r}")
                c.sendall(raw_response)
            except Exception as e:
                print(f"[ERROR] TCP gateway: {e!r}")
                traceback.print_exc()
                c.sendall(b"(ERROR)\n")
            finally:
                c.close()

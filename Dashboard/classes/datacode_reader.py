import re
import socket
import time
class DatacodeReader:
    def __init__(self, db, 
                 camera_ip: str,
                 camera_inport: int,
                 camera_outport: int,
                 trigger_cmd: bytes,
                 trigger_cmd_robotics: bytes,
                 change_job: bytes):
        self.db = db
        self.camera_ip = camera_ip
        self.camera_inport = camera_inport
        self.camera_outport = camera_outport
        self.trigger_cmd = trigger_cmd
        self.trigger_cmd_robotics = trigger_cmd_robotics
        self.change_job = change_job

    def recv_until(self, sock, terminators=(b"\n", b"\r\n"), timeout=2.0, max_bytes=4096):
        sock.settimeout(timeout)
        chunks = []
        total = 0
        try:
            while total < max_bytes:
                b = sock.recv(256)
                if not b:
                    break
                chunks.append(b)
                total += len(b)
                joined = b"".join(chunks)
                if any(joined.endswith(t) for t in terminators):
                    break
        except socket.timeout:
            pass
        return b"".join(chunks)

    def scan_raw(self) -> str:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cmd_socket:
            cmd_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            cmd_socket.settimeout(5.0)
            cmd_socket.connect((self.camera_ip, self.camera_inport))

            print(f"[datacode] Sending job change: {self.change_job!r}")
            cmd_socket.sendall(self.change_job)
            time.sleep(2)

            print(f"[datacode] Sending trigger: {self.trigger_cmd!r}")
            cmd_socket.sendall(self.trigger_cmd)
        
            #print(f"[datacode] Sending trigger: {self.trigger_cmd_robotics!r}")
            #cmd_socket.sendall(self.trigger_cmd_robotics)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as recv_socket:
            recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            recv_socket.settimeout(5.0)
            recv_socket.connect((self.camera_ip, self.camera_outport))

            raw_bytes = self.recv_until(recv_socket, timeout=2.0)
            raw = raw_bytes.decode("ascii", errors="ignore").strip()

        print(f"[datacode] Raw camera response: {raw!r}")

        return raw

    def parse_datacode_ids(self, raw_line: str) -> tuple[int, int]:
        """
        Expected datacode payload:
            code001
            code002
            ...

        The scanned datacode string is used to look up container_id and powder_id
        from the datacode_registry table.
        """
        if not raw_line:
            raise ValueError("Empty datacode response")

        cleaned = raw_line.strip()

        if not re.fullmatch(r"code\d{3}", cleaned):
            raise ValueError(f"Invalid datacode format: {raw_line}")

        row = self.db.fetch_datacode_entry(cleaned)
        if not row:
            raise ValueError(f"datacode registry entry not found: {cleaned}")

        container_id = row.get("container_id")
        powder_id = row.get("powder_id")

        if container_id is None or powder_id is None:
            raise ValueError(f"datacode registry entry {cleaned} is missing container_id or powder_id")

        return {
            "powder_id": powder_id,
            "container_id": container_id
        }

    # is this redundant?
    def resolve_powder(self, powder_id: int) -> dict:
        row = self.db.fetch_powder_by_id(powder_id)
        if not row:
            raise ValueError(f"Container with container_id {powder_id} not found")

        return {
            "powder_id": int(row["powder_id"]),
            "powder_name": str(row["powder_name"]),
            "bulk_density": float(row["bulk_density"]),
            "cas_number": str(row["cas_number"]),
            "flowability": str(row["flowability"]),
            "status": str(row["status"]),
        }

    # is this redundant?
    def resolve_container(self, container_id: int) -> dict:
        row = self.db.fetch_container_by_id(container_id)
        if not row:
            raise ValueError(f"Container with container_id {container_id} not found")

        return {
            "container_id": int(row["container_id"]),
            "height_c_mm": float(row["height_w_cap_mm"]),
            "height_mm": float(row["height_wo_cap_mm"]),
            "mouth_d_mm": float(row["mouth_diameter_mm"]),
            "mouth_sh_mm": float(row["mouth_shoulder_height_mm"]),
            "length_mm": float(row["length_mm"]),
            "diameter_mm": float(row["diameter_mm"]),
            "empty_weight_g": float(row["empty_weight_g"]),
            "shape": str(row["shape"]).upper(),
        }

    def compute_container_volume_ml(
        self,
        height_mm: float,
        mouth_sh_mm: float,
        diameter_mm: float,
        length_mm: float,
        shape: str,
    ) -> float:
        # assumed wall thickness in mm
        thickness = 1
        if shape == "CYLINDRICAL":
            r = diameter_mm / 2.0
            vol_mm3 = 3.141592653589793 * (r - thickness) * (r - thickness) * (height_mm-mouth_sh_mm- thickness)
        elif shape == "CUBICAL":
            vol_mm3 = (length_mm ) * (length_mm ) * (height_mm-mouth_sh_mm)
        else:          
            raise ValueError(f"Unsupported container shape: {shape}")

        vol_ml = vol_mm3 / 1000.0
        return vol_ml
    

    def compute_weight_empty(self,container_id: int) -> float:
        
        row = self.resolve_container(container_id)
        weight_empty = row.get("empty_weight_g")
        print(f"[SER] Empty weight of container with cap: {weight_empty}")
        return weight_empty
    
    def compute_weight_full(self,powder_id: int, container_id: int) -> float:
        
        powder = self.resolve_powder(powder_id)
        cont = self.resolve_container(container_id)
        vol = self.compute_container_volume_ml(
            height_mm=cont["height_mm"],
            mouth_sh_mm=cont["mouth_sh_mm"],
            diameter_mm=cont["diameter_mm"],
            length_mm=cont["length_mm"],
            shape=cont["shape"],
        )
        density = powder.get("bulk_density")
        weight_empty = self.compute_weight_empty(container_id)
        print(f"density: {density}")
        weight_full = vol*density + weight_empty
        print(f"[SER] Full weight of the container for the powder:{powder_id} is {weight_full}")
        return weight_full
    
    def scan_and_resolve(self) -> dict:
        raw = self.scan_raw()
        datacode_row = self.parse_datacode_ids(raw)
        container_id = int(datacode_row["container_id"])
        powder_id = int(datacode_row["powder_id"])

        powder = self.resolve_powder(powder_id)
        cont = self.resolve_container(container_id)
        vol = self.compute_container_volume_ml(
            height_mm=cont["height_mm"],
            mouth_sh_mm=cont["mouth_sh_mm"],
            diameter_mm=cont["diameter_mm"],
            length_mm=cont["length_mm"],
            shape=cont["shape"],
        )
        full_weight = self.compute_weight_full(powder_id,container_id)
        return {
            "datacode_id": raw,
            "container_id": container_id,
            "powder_id": powder["powder_id"],
            "powder_name": powder["powder_name"],
            "bulk_density": powder["bulk_density"],
            "flowability": powder["flowability"],
            "height_c_mm": cont["height_c_mm"],
            "height_mm": cont["height_mm"],
            "mouth_d_mm": cont["mouth_d_mm"],
            "mouth_sh_mm": cont["mouth_sh_mm"],
            "length_mm": cont["length_mm"],
            "diameter_mm": cont["diameter_mm"],
            "empty_weight_g": cont["empty_weight_g"],
            "shape": cont["shape"],
            "volume_ml": vol,
            "full_weight_g": full_weight,
        }
 
"""
------ TILTING STATION CONTROL ------

While the ESP32 runs the .ino and additional files, this .py file is run by the user in order to wirelessly send
the message with the movement characteristics.

--- Note: ---
Before use, align the top gear so that the station is upright.

To control, send the controller a message indicating:
"{movement},{position},{speed}"

--- Modes: ---
TURN OFF MOTORS  - message = "Off,0,0"
TILT             - message = f"Tilt,{position},{speed}"
                        For position send a value between [0, 180).
ROTATECCW        - message = f"RotateCCW,{position},{speed}"
ROTATECW         - message = f"RotateCW,{position},{speed}"
                        For position (both cases) send a value between [0, 360).
FULLROTATION     - message = f"FullRotation,{position},{speed}"
                        -1 for position means 1 rotation CCW.
                         1 for position means 1 rotation CW.
GOHOME           - message = "Home,0,0"

--- Example: ---

message = "Tilt,90,0"
Type: Tilt,90,0
0 is default speed.

message = "RotateCW,120,0"
Type: RotateCW,120,0
0 is default speed.

message = "FullRotation,2,0"
Type: FullRotation,2,0
0 is default speed.

For the gripper:
- reference state is fully closed = 0.0 cm
- maximum opening = 5.5 cm
- "GripperOpen,2.0,0"  -> opens 2.0 cm more
- "GripperClose,1.5,0" -> closes 1.5 cm more
- command is clamped between 0.0 cm and 5.5 cm

Speed refers to the wait time between each pulse of the stepper, in microseconds.
Use values greater than 1000. Bigger values mean slower movement.
For the gripper, speed 0 uses the default speed from code.

--- Note: ---
Before use, align the top gear so that the station is upright.


Speed is measured in microseconds. It is the amount of delay between each signal pulse. 
Use numbers greater than 1000. Bigger numbers mean slower movement.

"""
import socket
import json

class POTS:
    def __init__(self, ip: str , port: int, discovery_port: int):
        self.ip = ip
        self.port = port
        self.discovery_port = discovery_port
        self.sock=None
       
    def discover_pots(self, timeout: float=3):
        """
        Broadcast a discovery request and wait for the PoTS to respond.

        Returns:
            dict with keys:
                ip
                tcp_port
                version
                serial

            or None if not found.
        """

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock.setsockopt(socket.SOL_SOCKET,
                        socket.SO_BROADCAST,
                        1)

        sock.settimeout(timeout)

        try:
            sock.sendto(
                b"DISCOVER_POTS",
                ("192.168.12.255", self.discovery_port)
            )

            while True:

                data, addr = sock.recvfrom(1024)

                try:
                    info = json.loads(data.decode())

                except json.JSONDecodeError:
                    continue

                if info.get("device") != "POTS":
                    continue

                info["ip"] = addr[0]

                return info

        except socket.timeout:
            return None

        finally:
            sock.close()

    def connect(self):

        if self.sock is not None:
            return

        device = None

        for _ in range(3):
            device = self.discover_pots(timeout=2)
            if device:
                break

        if device is None:
            raise RuntimeError("PoTS not found after 3 discovery attempts.")

        self.ip = device["ip"]
        self.port = device["tcp_port"]

        print(f"[PoTS] Found at {self.ip}:{self.port}")

        self.sock = socket.socket(socket.AF_INET,
                                socket.SOCK_STREAM)

        self.sock.setsockopt(socket.IPPROTO_TCP,
                            socket.TCP_NODELAY,
                            1)

        self.sock.connect((self.ip, self.port))

        print("[PoTS] Connected")

    def disconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            finally:
                self.sock = None
                print("[PoTS] Disconnected")

    def send(self, command: str)-> str:
        command = command.strip()+"\n"
        try:
            self.connect()
            if self.sock is None:
                return "[PoTS] Connection failed\n"
            
            payload = command.encode("utf-8")
            print(f"[PoTS TX RAW] {payload!r}")
            self.sock.sendall(payload)
            #self.sock.close()
            return "[PoTS] OK\n"

        except Exception as e:
            print(f"[PoTS] Send failed for command={command!r}: {e!r}")
            self.disconnect()
            return "[PoTS] error sending command\n"

    def pots_home(self)-> str:
        return self.send(f"Home,0,0")
            
    def pots_tilt(self, angle: float)-> str:
        return self.send(f"Tilt,{angle},0")
            
    def pots_motor_off(self)-> str:
        return self.send("Off,0,0")
        
    def pots_fullrotate(self, direction: int)-> str:
        return self.send(f"FullRotation,{direction},2000")
    
    def pots_CCWrotate(self, angle:float)-> str:
        return self.send(f"RotateCCW,{angle},2000")
        
    def pots_CWrotate(self, angle:float) -> str:
        return self.send(f"RotateCW,{angle},2000")
    
    def pots_open(self, length:float) -> str:
        return self.send(f"GripperOpen,{length},0")
    
    def pots_close(self, length:float) -> str:
        return self.send(f"GripperClose,{length},0")
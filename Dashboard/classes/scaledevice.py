import re
import telnetlib
import serial
import time

class WeighScale:
    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port

    def _connect(self):
        return telnetlib.Telnet(self.ip, self.port, timeout=10)

    def _send(self, command: bytes, timeout: int = 3) -> str:
        tn = self._connect()
        try:
            tn.write(command)
            return tn.read_until(b"\n", timeout=timeout).decode("utf-8").strip()
        finally:
            tn.close()

    def read_weight(self) -> float:
        last_response = ""
        deadline = time.time() + 1.5

        while time.time() < deadline:
            response = self._send(b"SI\r\n", timeout=2)
            if response:
                last_response = response
            match = re.search(r"[-+]?\d*\.\d+|\d+", response)
            if match:
                return float(match.group())
            time.sleep(0.05)

        raise ValueError(f"Could not parse weight from response: {last_response}")

    def tare(self) -> bool:
        return self._send(b"T\r\n").startswith("S")

    def zero(self) -> bool:
        return self._send(b"Z\r\n").startswith("S")


class PCEScale:

    def __init__(self, port: str, baudrate: int):
        self.port = port
        self.baudrate = baudrate
        self.offset = 0.0

    def read_weight_once(self, timeout=2):
        try:
            with serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            ) as ser:

                ser.reset_input_buffer()

                start_time = time.time()

                while time.time() - start_time < timeout:
                    raw = ser.readline()

                    if not raw:
                        continue

                    line = raw.decode(errors='ignore').strip()
                    #print(f"[READ] {line}")

                    weight = self._parse(line)
                    if weight is not None:
                        return weight

                print("[WARN] No valid weight received")
                return None

        except Exception as e:
            print(f"[ERROR] {e}")
            return None

    def tare(self):
        try: 
            tare_offset = self.read_weight_once()
            if tare_offset is not None:
                self.offset = tare_offset

        except Exception as e:
            print(f"[ERROR] {e}")
            return None
        
    def get_cont_weight(self):
        try: 
            weight = self.read_weight_once()
            if weight is not None:
                return weight-self.offset 
            
        except Exception as e:
            print(f"[ERROR] {e}")
            return None
        
    
    def _parse(self, line):
        try:
            match = re.search(r"[-+]?\d*\.?\d+", line)
            if match:
                return float(match.group())
            return None
        except:
            return None
import os
import sys
import subprocess
from threading import Thread

if os.geteuid() != 0:
    subprocess.check_call(["sudo", sys.executable] + sys.argv)
    sys.exit()

print("Running with sudo privileges.")

# CONFIG 
# Server config
GATEWAY_HOST = "0.0.0.0"
GATEWAY_PORT = 3002

# Dashboard config
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000

# Mettler Toledo XSR303SN scale network config (TCP/IP)
SCALE_IP = "192.168.12.240"
SCALE_PORT = 8010

# PCE-PB600 scale config (Serial)
SCALE2_PORT = '/dev/ttyUSB0'
SCALE2_BAUDRATE = 9600

# POTS config
POTS_IP = None  # Set to None to auto-discover
POTS_PORT = 80
DISCOVERY_PORT = 4210

# Database config
DB_PATH = os.environ.get("LOCAL_DB_PATH", "local_lab.db")

# Logging config
DEFAULT_LOG_FILE = "live_weight_log.csv"
VALIDATION_LOG_DIRECTORY = "validation_logs"
DASHBOARD_EXPORT_DIRECTORY = "dashboard_exports"
ENABLE_VALIDATION_EXPORTS = False  # Set to True to enable validation exports, False to disable

# Base paths used for SQLite, static files, and HTML templates.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# Datacode reader config
CAMERA_IP = "192.168.12.123"
CAMERA_PORT = 2006
CAMERA_OUTPORT = 2005
TRIGGER_CMD = b"TRG00\r\n"
TRIGGER_CMD_ROBOTICS = b"TRR00\r\n"
CHANGE_JOB_CMD = b"CJB040\r\n"

# #Crisscross Config
# CRISSCROSS_LENGTH = 50.0
# CRISSCROSS_BREADTH = 50.0
# STEP_PATH=r"C:\Users\francis3683\Desktop\RoX Swab Test\step_click_play_button\step_click_play_button\assembly_final_2.step"


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

# GATEWAY
from Gatewayserver import GatewayServer

# DASHBOARD
from Dashboardserver import DashboardServer

#Path Generator VTK
#from classes.Crisscrosspath import ZigzagWaypointGenerator

# SYSTEM 
class PowderDosingSystem:
    def __init__(self, static_dir: str = "."):
        self.scale = WeighScale(SCALE_IP, SCALE_PORT)
        self.scale2 = PCEScale(SCALE2_PORT, SCALE2_BAUDRATE)
        self.db = LabDatabase(DB_PATH)
        self.pots = POTS(POTS_IP, POTS_PORT, DISCOVERY_PORT)
        self.visualizer = VisualizationState()
        self.logger = WeightLogger(DEFAULT_LOG_FILE, VALIDATION_LOG_DIRECTORY, DASHBOARD_EXPORT_DIRECTORY, ENABLE_VALIDATION_EXPORTS)
        self.datacode_reader = DatacodeReader(self.db, CAMERA_IP, CAMERA_PORT, CAMERA_OUTPORT, TRIGGER_CMD, TRIGGER_CMD_ROBOTICS, CHANGE_JOB_CMD)
        self.dosing = Dosing(self.db, self.scale, self.scale2, self.datacode_reader, self.pots)
        self.gateway = GatewayServer(GATEWAY_HOST, GATEWAY_PORT, self.scale, self.scale2, self.db, self.pots, self.visualizer, self.logger,self.datacode_reader, self.dosing)
        self.dashboard = DashboardServer(DASHBOARD_HOST, DASHBOARD_PORT, TEMPLATE_DIR, self.scale, self.scale2, self.db, self.pots, self.visualizer, self.logger, self.datacode_reader, self.dosing,  static_dir=static_dir)
        #self.generator = ZigzagWaypointGenerator(STEP_PATH, CRISSCROSS_LENGTH,CRISSCROSS_BREADTH)
        
    def initialize(self) -> None:
        self.db.init_and_migrate()
        self.db.seed_containers_if_empty()
        self.db.seed_spatulas_if_empty()
        self.db.seed_powders_if_empty()
        self.db.seed_datacode_registry_if_empty()


    def run(self) -> None:
        self.initialize()
        Thread(target=self.dashboard.run, daemon=True).start()
        self.gateway.run()


if __name__ == "__main__":
    system = PowderDosingSystem(static_dir=".")
    system.run()

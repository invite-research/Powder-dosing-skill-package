# ROX Package Structure

## 1. What ROX is

ROX is a laboratory powder-dosing system. It combines:

- a Python dashboard for operators and data management;
- a hardware gateway for scales, the robot, the camera, and the tilting station;
- a local SQLite database for laboratory records;
- robot programs for the UR5e workstation;
- simulation and validation tools for checking dosing plans and robot motion;
- validation logs and exported reports.

The main Python application is in `Dashboard/`. The `programs/` folder contains robot-controller files and is not a Python package.

## 2. Repository tree

The tree below shows the complete functional structure. Repeated historical backups and generated validation exports are represented by filename patterns rather than every individual run folder.

```text
ROX/
├── README.md                               Main setup and operating notes
├── ROX_PACKAGE_STRUCTURE.md                This handover guide
├── Dashboard/                              Main Python application
│   ├── Main.py                              Main launcher; starts gateway and dashboard
│   ├── Dashboardserver.py                   Web dashboard server/routes
│   ├── Gatewayserver.py                     Hardware TCP gateway
│   ├── wsgi.py                              WSGI entry point for deployment
│   ├── api/                                 API route definitions
│   │   └── routes.py                         
│   ├── classes/                             Application domain and hardware classes
│   │   ├── datacode_reader.py                Camera/datacode reader integration
│   │   ├── labdatabase.py                    SQLite/database access
│   │   ├── scaledevice.py                    Network and serial scale access
│   │   ├── tilting_station.py                Tilting-station communication
│   │   ├── visualization.py                  Charts and report visualizations
│   │   └── weightlogger.py                   Weight logging
│   ├── templates/                            HTML dashboard pages
│   │   ├── home.html                         Home page
│   │   ├── index.html                        Live dosing page
│   │   ├── results.html                      Completed-run results
│   │   ├── containers.html                   Container management
│   │   ├── powders.html                      Powder management
│   │   ├── spatulas.html                     Spatula management
│   │   └── datacode_registry.html            Datacode registry management
│   ├── static/                               Images and frontend assets
│   └── local_lab.db                          Application database copy (main database local)
│
├── PoTS_final/                              Tilting station project
│   └── PoTS/
│       ├── README.md                         Tilting-station project notes
│       ├── OperatingInstructions.md          Operating instructions
│       ├── Code/
│       │   ├── ulab_program.py               MicroPython/user control program
│       │   ├── user_program.py               Main user program
│       │   ├── user_program copy.py          Backup/copy of user program
│       │   └── tilting_station/              Arduino tilting-station firmware
│       │       ├── tilting_station.ino
│       │       ├── Discovery.cpp
│       │       ├── Discovery.h
│       │       ├── other_functions.h
│       │       └── pins_and_variables.h
│       ├── Design/                            CAD and 3D models
│       │   ├── assembly_final v9.f3z
│       │   ├── external_structure.stl
│       │   └── internal_structure.stl
│       └── OtherFiles/
│           ├── accuracy_measurements.xlsx     Accuracy measurements
│           ├── electrical_configuration.png   Electrical setup image
│           └── Pictures/                       Explanatory system/coordinate images
│
├── programs/                                 UR5e robot-controller project files (Backup files)
│   ├── 01 Installations/                      Robot installation files
│   ├── 02 Main Routines/                     Main robot routines
│   ├── 03 Sub Routines/                      Reusable robot subroutines
│   ├── 04 Scripts/                           Robot script files and action scripts
│   ├── .SensoPart/calibsets/                 SensoPart camera/calibration data
│   ├── new folder_1/                         Additional robot project material
│   └── historical project files              *.old0-*.old9, *.bak0-*.bak9, *.txt,
│                                             *.urp, *.installation, *.variables
```

## 3. How the main pieces fit together

1. An operator starts `Dashboard/Main.py`.
2. The launcher initializes the database and starts the dashboard on port `5000`.
3. The hardware gateway listens on port `3002` and communicates with the scales, robot, camera, and tilting station.
4. The dashboard uses the classes in `Dashboard/classes/` to plan and execute powder dosing.
5. The robot executes routines from `programs/`.
6. Measurements are written to the SQLite database and CSV logs.
7. Validation and dashboard reports are written under `validation_logs/`.

## 4. Important boundaries for a third party

### Source code

The application source is primarily in `Dashboard/`. Changes to dosing behavior, device communication, database access, or planning should normally be made in `classes/`, `api/`, `Dashboardserver.py`, `Gatewayserver.py`, or `Main.py`.

### Robot and hardware files

The files in `programs/` are intended as the UR5e robot controller backup. They may include active programs as well as historical backups. The files in `PoTS_final/` describe and control the separate tilting station.

### Generated and historical data

`local_lab.db`, `live_weight_log.csv`, `validation_logs/`, simulation spreadsheets, plots, and dashboard export folders are data or generated results. They are useful for traceability and analysis but are not normally required to understand the application source.

### Local configuration and credentials

Device IP addresses, ports, camera commands, database paths, and log paths are configured in `Dashboard/Main.py`. `apikeyconnector.txt` contains connector connection details or credentials and should be handled as confidential. Do not publish it or commit secrets to a public repository.

## 5. Running the application

The expected environment is Linux with Python 3.11 and the packages in `requirements.txt`. From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd "Dashboard"
python3.11 Main.py
```

This project is hardware-dependent. A third party should confirm the device network addresses, scale ports, robot availability, camera configuration, and database path before starting a live dosing run. The complete setup notes are in `README.md`.

## 6. Folders that are local or generated

The checkout may also contain `.git/`, `.vscode/`, `venv/`, and `__pycache__/`. These are version-control metadata, editor settings, a local Python environment, and Python bytecode caches respectively. They are not application source and should not be treated as required runtime components.
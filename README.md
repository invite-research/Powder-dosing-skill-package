# ROX Adaptive Powder Dosing
ROX is a Python-based robotic powder-dosing platform that performs geometry-adaptive dosing from laboratory containers. It integrates a web dashboard, TCP gateway, scales, datacode reader, and tilting station, with SQLite for laboratory data.

This project runs the ROX powder dosing workflow used in the lab. It combines:

- a TCP gateway for hardware commands and scale reads
- a web dashboard for monitoring and managing containers, powders, spatulas, and datacode records
- a local SQLite database and CSV/SVG export logs for validation and reporting

The main launcher starts both the gateway and the dashboard together.

## What you need

- Linux with Python 3.11 installed
- Access to the lab devices and network
- The Python packages listed in `requirements.txt`
- `pip`, provided by the Python installation, to install the packages

If you do not already have Python 3.11, install it first and verify it with `python3.11 --version`.

## Environment and component requirements

The following table separates software required to run or develop ROX from software used by the connected laboratory equipment. Versions are pinned only where they are recorded in this repository.

| Component | Environment requirement | Version | Notes |
|---|---|---|---|
| Python backend | Python runtime | 3.11 | Project target version. The current launcher uses Linux-specific `sudo` behavior. |
| Python package installer | `pip` | Not pinned | Included with, or installed alongside, Python. Used to install `requirements.txt`. |
| SQLite | Python `sqlite3` module and SQLite runtime | Not pinned by ROX; local Windows check: SQLite 3.50.4 | SQLite is accessed through Python's standard library. The runtime version depends on the Python installation. |
| Arduino firmware | Arduino IDE with ESP32 board support | Not recorded in repository | The firmware source is under `PoTS_final/PoTS/Code/tilting_station/`. |
| HTML frontend | Modern desktop browser with JavaScript, `fetch`, WebSocket-compatible networking, HTML5, and CSS support | No minimum browser version pinned | Current Chrome, Firefox, or Edge releases are the expected targets. |

### Browser and hardware notes

The frontend is served by Flask and uses browser JavaScript to communicate with the dashboard. The repository does not define a browser compatibility matrix, so a current Chrome, Firefox, or Microsoft Edge release should be used for live operation.

The tilting-station firmware runs on an ESP32 and includes the `ArduinoJson` library. The repository does not record the Arduino IDE, ESP32 board package, or ArduinoJson library versions; these should be captured from the working hardware installation before reproducing the setup.

## Component type, license, and version

| Component | Type | License | Version in this repository |
|---|---|---|---|
| Python | Open source programming language | Python Software Foundation License 2.0 | 3.11 target |
| SQLite | Open source/public-domain embedded database | Public domain | Not pinned by ROX; local check: 3.50.4 |
| Flask | Open source Python web framework | BSD-3-Clause | 3.0.3 |
| NumPy | Open source Python numerical library | BSD-3-Clause | 2.0.1 |
| pandas | Open source Python data-processing library | BSD-3-Clause | 2.2.2 |
| SciPy | Open source Python scientific-computing library | BSD-3-Clause | 1.14.0 |
| Matplotlib | Open source Python plotting library | Matplotlib License, based on PSF/BSD terms | 3.9.2 |
| openpyxl | Open source Python Excel-file library | MIT | 3.1.5 |
| PyBullet | Open source physics and robotics simulator | zlib License | 3.2.6 |
| pyserial | Open source Python serial-communication library | BSD-3-Clause | 3.5 |
| SensoPart VISOR Robotic | Commercial machine-vision system and vendor integration | Proprietary/commercial | 2.0.6 in newer robot programs; 2.0.0 in older backups |
| Universal Robots APIs / URScript | Vendor-supplied robot programming and integration tools | Proprietary/vendor-supplied | UR Connect 2.3.3 in newer programs; 1.13.60 in older programs |
| Arduino IDE | Open source embedded-development environment | GPL-2.0-or-later | Not recorded in repository |
| ArduinoJson | Open source Arduino library | MIT | Not recorded in repository |
| ESP32 Arduino core | Open source Arduino board-support package | LGPL-2.1-or-later | Not recorded in repository |

The license entries describe the upstream software components, not ownership of the ROX application or laboratory data. For the commercial SensoPart and Universal Robots components, consult the vendor license supplied with the installed equipment. The repository contains historical robot programs with multiple vendor versions, so the exact version on a deployed robot must be checked on that robot/controller.

### Python standard-library modules

The application also uses modules such as `sqlite3`, `socket`, `re`, `time`, `typing`, `datetime`, `json`, `dataclasses`, `statistics`, `html`, `collections`, `csv`, `pathlib`, `subprocess`, `sys`, `os`, and `threading`.

If `pip` is missing, install or enable it with the Python installation, for example `python3.11 -m ensurepip --upgrade`.

The project currently imports `telnetlib` for the network scale. With the documented Python 3.11 environment, `telnetlib` is part of the standard library. `telnetlib3` is a windows version and is not used by the current source code . Python 3.13 and later removed `telnetlib`, so use Python 3.11 or update `Dashboard/classes/scaledevice.py` before moving to a newer Python version.

The current launcher is Linux-specific: `Dashboard/Main.py` uses `os.geteuid()` and relaunches with `sudo`. Running ROX directly on Windows therefore requires launcher and device-path changes; installing `telnetlib3` alone will not make the application Windows-compatible.

## Fresh setup on a new machine

If you are starting from scratch, install the repository and its dependencies in this order:

```bash
git clone <repository-url>
cd ROX
```

This project is organized as a single repository with the dashboard and gateway code inside [Dashboard/](/home/rox/ROX/Shantanu%20dashboard/). There is not a separate install step for each folder.

Then create the Python environment and install the project packages:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If you are on Ubuntu and need to build Python 3.11 yourself, install the common build tools first:

```bash
sudo apt update
sudo apt install -y build-essential libssl-dev zlib1g-dev \
  libncurses5-dev libncursesw5-dev libreadline-dev libsqlite3-dev \
  libgdbm-dev libdb5.3-dev libbz2-dev libexpat1-dev liblzma-dev \
  libffi-dev uuid-dev wget
```

The repository does not require a separate install step for the dashboard templates, static files, or validation scripts. Those are already included in the checkout.

## Install dependencies

From the repository root:

```bash
cd "/home/rox/ROX"
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
or to directly install inside python3.11

```bash
sudo /usr/local/bin/python3.11 -m pip install -r requirements.txt
```
If you are running the hardware serial scale, make sure `pyserial` is installed. It is already included in `requirements.txt`.

## Configure the project

Most runtime settings are defined in [Dashboard/Main.py] (Dashboard/Main.py).

Update these values before running :

- `SCALE_IP` and `SCALE_PORT` for the Mettler Toledo XSR303SN network scale
- `SCALE2_PORT` and `SCALE2_BAUDRATE` for the PCE serial scale
- `POTS_IP`, `POTS_PORT`, and `DISCOVERY_PORT` for the tilting station
- `CAMERA_IP`, `CAMERA_PORT`, `CAMERA_OUTPORT`, and trigger commands for datacode reading
- `DB_PATH` if you want the SQLite database stored somewhere else
- `DEFAULT_LOG_FILE`, `VALIDATION_LOG_DIRECTORY`, and `DASHBOARD_EXPORT_DIRECTORY` if you want different output locations

The default values are designed for the lab network shown in the code. If your devices are on different addresses or ports, update them before starting the system.

## How to run

Start the full system from the dashboard folder:

```bash
cd "/home/rox/ROX/Dashboard"
python3.11 Main.py
```

The script checks for root privileges and will relaunch itself with `sudo` if needed. When prompted, enter your password.

When it starts successfully:

- the gateway server listens on port `3002`
- the dashboard server listens on port `5000`
- the local database is initialized and seeded if empty

## What the user sees

- `/` opens the home page
- `/live` shows the live dosing view
- `/results` shows completed run results
- `/containers`, `/powders`, and `/spatulas` manage the corresponding records
- `/datacode_registry` manages the datacode registry

The dashboard is for monitoring and data management. The gateway handles the live hardware commands and weight responses.

## Output files

By default the system writes:

- `local_lab.db` for the SQLite database
- `live_weight_log.csv` for live weight logging
- `dashboard_exports/` for dashboard-generated SVG exports

Note: because the launcher runs with `sudo`, files created in `validation_logs/` and related outputs may become root-owned if you run the project as root. If you need to clean or edit those files later, prefer running from the same user consistently.

## Troubleshooting

- If the serial scale does not respond, verify the device path in `SCALE2_PORT` and check available ports with `ls /dev/tty*`.
- If the dashboard opens but hardware actions fail, confirm the IP addresses and ports in `Main.py` match the lab equipment.
- If imports fail, re-check that the virtual environment is activated and that `pip install -r requirements.txt` completed successfully.

## Simulation and Python setup notes

The repository also contains simulation and validation helpers under `Dashboard/Simulation Validations/` and related scripts. Those tools use the same Python environment and package set.

If you need to build Python 3.11 manually on Ubuntu, the original notes used:

```bash
sudo apt update
sudo apt install -y build-essential libssl-dev zlib1g-dev \
  libncurses5-dev libncursesw5-dev libreadline-dev libsqlite3-dev \
  libgdbm-dev libdb5.3-dev libbz2-dev libexpat1-dev liblzma-dev \
  libffi-dev uuid-dev wget
wget https://www.python.org/ftp/python/3.11.15/Python-3.11.15.tar.xz
tar -xf Python-3.11.15.tar.xz
cd Python-3.11.15
./configure --enable-optimizations --prefix=/usr/local
make -j$(nproc)
sudo make altinstall
python3.11 --version
```

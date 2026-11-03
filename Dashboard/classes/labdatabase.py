
import sqlite3
from datetime import datetime
from typing import Optional, List


class LabDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=3)

    def table_columns(self, table_name: str) -> set[str]:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table_name});")
            return {row[1] for row in cur.fetchall()}

    def ensure_column(self, table: str, col: str, sql_type: str, default_sql: Optional[str] = None) -> None:
        cols = self.table_columns(table)
        if col in cols:
            return
        with self.connect() as conn:
            cur = conn.cursor()
            if default_sql is None:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {sql_type};")
            else:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {sql_type} DEFAULT {default_sql};")
            conn.commit()
            print(f"[DB] Added column {table}.{col} ({sql_type})")

    def init_and_migrate(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS containers (
                    container_id INTEGER PRIMARY KEY,
                    height_w_cap_mm REAL NOT NULL,
                    height_wo_cap_mm REAL NOT NULL,
                    mouth_diameter_mm REAL NOT NULL,
                    mouth_shoulder_height_mm REAL NOT NULL,
                    length_mm REAL NOT NULL DEFAULT 0,
                    diameter_mm REAL NOT NULL DEFAULT 0,
                    empty_weight_g REAL NOT NULL DEFAULT 0,
                    shape TEXT NOT NULL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS spatulas (
                    slot_id INTEGER PRIMARY KEY,
                    spatula_name TEXT NOT NULL,
                    sdepth_mm REAL NOT NULL,
                    slength_mm REAL NOT NULL,
                    volumes_ml REAL NOT NULL,
                    retention_default_theta REAL NOT NULL,
                    spatula_length_mm REAL NOT NULL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS datacode_registry (
                    datacode_id TEXT PRIMARY KEY,
                    container_id INTEGER,
                    powder_id INTEGER,
                    powder_name TEXT,
                    container_type TEXT,
                    status TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS powders (
                    powder_id INTEGER PRIMARY KEY,
                    powder_name TEXT NOT NULL,
                    cas_number TEXT NOT NULL,
                    bulk_density REAL NOT NULL,
                    flowability TEXT NOT NULL,
                    status TEXT NOT NULL
                );
                """
            )
            conn.commit()

    # Containers 
    def seed_containers_if_empty(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM containers;")
            n = cur.fetchone()[0]
            if n and n > 0:
                return
            rows = [
                (101, 152.0, 149.0, 66.5, 24.0, 0.0, 70.0, 64.4, "cylindrical"),
                (102, 158.0, 155.0, 39.0, 44.0, 0.0, 77.0, 69.200, "cylindrical"),
                (103, 134.0, 128, 33.0, 30, 0.0, 61.0, 37.4, "cylindrical"),
                (201, 167, 162.0, 42.5, 56.0, 75.0, 0.0, 62,"cubical"),
                (202, 135, 129.5, 35.0, 46.4, 59.0, 0.0, 39.8, "cubical"),
                (203, 110, 106, 54.0, 40, 80.5, 0.0, 45.6, "cubical"),
            ]
            cur.executemany(
                """
                INSERT INTO containers
                (container_id, height_w_cap_mm, height_wo_cap_mm, mouth_diameter_mm, mouth_shoulder_height_mm, length_mm, diameter_mm, empty_weight_g, shape)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                rows,
            )
            conn.commit()
            print("[DB] Seeded initial containers (IDs 1-4).")
    
    def fetch_container_by_id(self, container_id: int) -> Optional[dict]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM containers WHERE container_id = ?;", (container_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        
    def fetch_all_containers(self) -> list[dict]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM containers ORDER BY container_id;")
            return [dict(r) for r in cur.fetchall()]

    def insert_container(
        self,
        container_id: int,
        Hc: float,
        h: float,
        mouth_d: float,
        mouth_sh: float,
        length: float,
        diameter: float,
        empty_weight_g: float,
        shape: str
    ) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO containers
                (container_id, height_w_cap_mm, height_wo_cap_mm, mouth_diameter_mm, mouth_shoulder_height_mm, length_mm, diameter_mm, empty_weight_g, shape)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(container_id) DO UPDATE SET
                    height_w_cap_mm=excluded.height_w_cap_mm,
                    height_wo_cap_mm=excluded.height_wo_cap_mm,
                    mouth_diameter_mm=excluded.mouth_diameter_mm,
                    mouth_shoulder_height_mm=excluded.mouth_shoulder_height_mm,
                    length_mm=excluded.length_mm,
                    diameter_mm=excluded.diameter_mm,
                    empty_weight_g=excluded.empty_weight_g,
                    shape=excluded.shape
                """,
                (container_id, Hc, h, mouth_d, mouth_sh, length, diameter, empty_weight_g, shape),
            )
            conn.commit()

    def delete_container(self, container_id: int) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM containers WHERE container_id=?;", (container_id,))
            conn.commit()
    
    #  Spatulas  
    def seed_spatulas_if_empty(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM spatulas;")
            n = cur.fetchone()[0]
            if n and n > 0:
                return
            rows = [
                (1, "spatula_L", 15.0, 32.0, 5.0, 0.0, 0.182),
                (2, "spatula_M", 10.0, 21.0, 1.25, 0.0, 0.182),
                (3, "spatula_S", 8.0, 12.6, 0.156, 0.0, 0.182),
                (4, "spatula_flat_M", 1.0, 40.0, 2.2, 0.0, 0.182),
                (5, "spatula_flat_S", 0.5, 32.0, 1.2, 0.0, 0.182),
            ]
            cur.executemany(
                """
                INSERT INTO spatulas (slot_id, spatula_name, sdepth_mm, slength_mm, volumes_ml, retention_default_theta, spatula_length_mm)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                rows,
            )
            conn.commit()
            print("[DB] Seeded default spatulas.")

    def fetch_spatula_by_id(self, slot_id: int) -> Optional[dict]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM spatulas WHERE slot_id = ?;", (slot_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def fetch_all_spatulas(self) -> list[dict]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM spatulas ORDER BY slot_id;")
            return [dict(r) for r in cur.fetchall()]
        
    def fetch_spatula_by_name(self, spatula_name: str) -> Optional[int]:

        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                "SELECT slot_id FROM spatulas WHERE spatula_name = ?;",
                (spatula_name,)
            )
            row = cur.fetchone()
            if row is None:
                print(f"[DB] No spatula found for name={spatula_name!r}")
                return None
            slot_id = row["slot_id"]
            print(f"[DB] Found slot_id={slot_id} for {spatula_name}")
            return slot_id
        
    def insert_spatula(self, slot_id: int, spatula_name: str, sdepth_mm: float, slength_mm: float, volumes_ml: float, retention_default_theta: float, spatula_length_mm: float) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO spatulas (slot_id, spatula_name, sdepth_mm, slength_mm, volumes_ml, retention_default_theta, spatula_length_mm)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(slot_id) DO UPDATE SET
                    spatula_name=excluded.spatula_name,
                    sdepth_mm=excluded.sdepth_mm,
                    slength_mm=excluded.slength_mm,
                    volumes_ml=excluded.volumes_ml,
                    retention_default_theta=excluded.retention_default_theta,
                    spatula_length_mm=excluded.spatula_length_mm
                """,
                (slot_id, spatula_name, sdepth_mm, slength_mm, volumes_ml, retention_default_theta, spatula_length_mm),
            )
            conn.commit()

    def delete_spatula(self, slot_id: str) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM spatulas WHERE slot_id=?;", (slot_id,))
            conn.commit()

    #- powders 
    def seed_powders_if_empty(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM powders;")
            n = cur.fetchone()[0]
            if n and n > 0:
                return
            rows = [
                (1,"NACL", "7647-14-5", 1.28, "HIGH", "active"),
                (2,"MANNITOL", "7647-14-5", 0.574, "HIGH", "active"),
                (3,"CCS", "7647-14-5", 0.462, "MEDIUM",  "active"),
                (4,"MCC", "9004-34-6", 0.333, "MEDIUM","active"),
                (5,"MAGNESIUM_STEARATE", "7647-14-5", 0.227, "LOW", "active"),
                (6,"LACTOSE_FINE", "7647-14-5", 0.4587, "LOW", "active"),
            ]
            cur.executemany(
                """
                INSERT INTO powders (powder_id, powder_name, cas_number, bulk_density, flowability, status)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                rows,
            )
            conn.commit()
            print("[DB] Seeded default Powdered powders.")

    def fetch_powder_by_id(self, powder_id: str) -> Optional[dict]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM powders WHERE powder_id = ?;", (powder_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def fetch_all_powders(self) -> list[dict]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM powders ORDER BY powder_id;")
            return [dict(r) for r in cur.fetchall()]

    def insert_powder(self, powder_id: int, powder_name: str, cas_number: str,
                    bulk_density: float, flowability: str, status: str) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO powders 
                (powder_id, powder_name, cas_number, bulk_density, flowability, status)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(powder_id) DO UPDATE SET
                    powder_name=excluded.powder_name,
                    cas_number=excluded.cas_number,
                    bulk_density=excluded.bulk_density,
                    flowability=excluded.flowability,
                    status=excluded.status
                """,
                (powder_id, powder_name, cas_number, bulk_density, flowability, status),
            )
            conn.commit()
    
    def fetch_powder_id_by_name(self, powder_name: str) -> Optional[int]:

        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                "SELECT powder_id FROM powders WHERE powder_name = ?;",
                (powder_name,)
            )
            row = cur.fetchone()
            if row is None:
                print(f"[DB] No powder found for name={powder_name!r}")
                return None
            pow_id = row["powder_id"]
            #print(f"[DB] Found powder_id={pow_id} for {powder_name}")

            return pow_id
            
    def delete_powder(self, powder_id: str) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM powders WHERE spatula_name=?;", (powder_id,))
            conn.commit()
    
    #  datacode Registry 
    def seed_datacode_registry_if_empty(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM datacode_registry;")
            n = cur.fetchone()[0]
            if n and n > 0:
                return
            now = datetime.now().isoformat(timespec="seconds")
            rows = [
                ("code001", 101, 1, "NACL", "cylindrical", "active", "Seeded example", now, now),
                ("code002", 201, 2, "MANNITOL", "cubical", "active", "Seeded example", now, now),
            ]
            cur.executemany(
                """
                INSERT INTO datacode_registry
                (datacode_id, container_id, powder_id, powder_name, container_type, status, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
            print("[DB] Seeded datacode registry.")

    def create_datacode_entry(
        self,
        datacode_id: str,
        container_id: Optional[int] = None,
        powder_id: Optional[int] = None,
        powder_name: str = "",
        container_type: str = "",
        status: str = "active",
        notes: str = "",
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT datacode_id FROM datacode_registry WHERE datacode_id = ?;", (datacode_id,))
            if cur.fetchone():
                raise ValueError(f"{datacode_id} already exists")
            cur.execute(
                """
                INSERT INTO datacode_registry
                (datacode_id, container_id, powder_id, powder_name, container_type, status, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (datacode_id, container_id, powder_id, powder_name, container_type, status, notes, now, now),
            )
            conn.commit()

    def update_datacode_entry(
        self,
        datacode_id: str,
        container_id: Optional[int] = None,
        powder_id: Optional[int] = None,
        powder_name: str = "",
        container_type: str = "",
        status: str = "active",
        notes: str = "",
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT datacode_id FROM datacode_registry WHERE datacode_id = ?;", (datacode_id,))
            if not cur.fetchone():
                raise ValueError(f"{datacode_id} does not exist")
            cur.execute(
                """
                UPDATE datacode_registry
                SET container_id = ?,
                    powder_id = ?,
                    powder_name = ?,
                    container_type = ?,
                    status = ?,
                    notes = ?,
                    updated_at = ?
                WHERE datacode_id = ?
                """,
                (container_id, powder_id, powder_name, container_type, status, notes, now, datacode_id),
            )
            conn.commit()

    def delete_datacode_entry(self, datacode_id: str) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM datacode_registry WHERE datacode_id = ?;", (datacode_id,))
            conn.commit()

    def fetch_datacode_entry(self, datacode_id: str) -> Optional[dict]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM datacode_registry WHERE datacode_id = ?;", (datacode_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        
    def fetch_id_by_powder(self, powder_id: int) -> Optional[dict]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            self.id=cur.execute("SELECT * FROM datacode_registry WHERE powder_id = ?;", (powder_id,))
            return id

    def fetch_all_datacode_entries(self, search: str = "") -> List[dict]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if search:
                like = f"%{search}%"
                cur.execute(
                    """
                    SELECT * FROM datacode_registry
                    WHERE datacode_id LIKE ?
                       OR powder_name LIKE ?
                       OR container_type LIKE ?
                       OR status LIKE ?
                       OR notes LIKE ?
                    ORDER BY datacode_id ASC
                    """,
                    (like, like, like, like, like),
                )
            else:
                cur.execute("SELECT * FROM datacode_registry ORDER BY datacode_id ASC;")
            return [dict(r) for r in cur.fetchall()]



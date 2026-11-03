import os
import statistics
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory, url_for, redirect, render_template
from typing import Dict, Any, Optional

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

# DASHBOARD 
class DashboardServer:
    def __init__(self, host: str, port: int, template_folder: str, scale: WeighScale, scale2: PCEScale, db: LabDatabase, pots:POTS, visualizer: VisualizationState, logger: WeightLogger, datacode_reader: DatacodeReader, dosing: Dosing,  static_dir: str = "."):
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
        self.static_dir = static_dir
        self.app = Flask(__name__,template_folder=template_folder)
        self._register_routes()
        self._configure_logging()
    
    def _configure_logging(self):
        import logging
        logging.getLogger("werkzeug").disabled = True

    @staticmethod
    def _parse_int_field(value: str) -> Optional[int]:
        value = (value or "").strip()
        if value == "":
            return None
        return int(value)

    def _datacode_form_to_data(self, form) -> Dict[str, Any]:
        return {
            "datacode_id": form.get("datacode_id", "").strip(),
            "container_id": self._parse_int_field(form.get("container_id", "")),
            "powder_id": self._parse_int_field(form.get("powder_id", "")),
            "powder_name": form.get("powder_name", "").strip(),
            "container_type": form.get("container_type", "").strip(),
            "status": form.get("status", "active").strip(),
            "notes": form.get("notes", "").strip(),
        }

    def _register_routes(self) -> None:
        app = self.app
        
        @app.route("/")
        def home():
            return send_from_directory(self.static_dir, "templates/home.html")

        @app.route("/live")
        def live_page():
            return send_from_directory(self.static_dir, "templates/index.html")

        @app.route("/results")
        def results_page():
            return send_from_directory(self.static_dir, "templates/results.html")

        @app.route("/containers")
        def containers_page():
            return send_from_directory(self.static_dir, "templates/containers.html")
        
        @app.route("/powders")
        def powders_page():
            return send_from_directory(self.static_dir, "templates/powders.html")
        
        @app.route("/spatulas")
        def spatulas_page():
            return send_from_directory(self.static_dir, "templates/spatulas.html")
        
        @app.route("/containers.json")
        def containers_json():
            return jsonify(self.db.fetch_all_containers())

        @app.route("/spatulas.json")
        def spatulas_json():
            return jsonify(self.db.fetch_all_spatulas())
        
        @app.route("/powders.json")
        def powders_json():
            return jsonify(self.db.fetch_all_powders())

        @app.route("/api/containers/insert", methods=["POST"])
        def api_containers_insert():
            try:
                j = request.get_json(force=True, silent=True) or {}
                self.db.insert_container(
                    int(j["container_id"]),
                    float(j["height_w_cap_mm"]),
                    float(j["height_wo_cap_mm"]),
                    float(j["mouth_diameter_mm"]),
                    float(j["mouth_shoulder_height_mm"]),
                    float(j.get("length_mm", 0) or 0),
                    float(j.get("diameter_mm", 0) or 0),                
                    float(j.get("empty_weight_g", 0) or 0),
                    str(j["shape"]),
                )
                return jsonify({"ok": True})
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 400

        @app.route("/api/containers/delete", methods=["POST"])
        def api_containers_delete():
            j = request.get_json(force=True, silent=True) or {}
            self.db.delete_container(int(j["container_id"]))
            return jsonify({"ok": True})

        @app.route("/api/import/containers", methods=["POST"])
        def api_import_containers():
            try:
                payload = request.get_json(force=True, silent=True) or {}

                if isinstance(payload, list):
                    rows = payload
                elif isinstance(payload, dict):
                    if isinstance(payload.get("containers"), list):
                        rows = payload["containers"]
                    elif isinstance(payload.get("items"), list):
                        rows = payload["items"]
                    else:
                        rows = [payload]
                else:
                    raise ValueError("Expected a JSON array or object")

                inserted = 0
                errors = []

                for index, row in enumerate(rows):
                    if not isinstance(row, dict):
                        errors.append({"index": index, "error": "row is not an object"})
                        continue

                    try:
                        container_id = int(row.get("container_id"))
                        self.db.insert_container(
                            container_id,
                            float(row.get("height_w_cap_mm", 0) or 0),
                            float(row.get("height_wo_cap_mm", 0) or 0),
                            float(row.get("mouth_diameter_mm", 0) or 0),
                            float(row.get("mouth_shoulder_height_mm", 0) or 0),
                            float(row.get("length_mm", 0) or 0),
                            float(row.get("diameter_mm", 0) or 0),
                            float(row.get("empty_weight_g", 0) or 0),
                            str(row.get("shape", "cylindrical") or "cylindrical"),
                        )
                        inserted += 1
                    except Exception as exc:
                        errors.append({
                            "index": index,
                            "container_id": row.get("container_id"),
                            "error": str(exc),
                        })

                return jsonify({"ok": True, "inserted": inserted, "errors": errors})
            except Exception as exc:
                return jsonify({"ok": False, "error": str(exc)}), 400
        
        @app.route("/api/powders/insert", methods=["POST"])
        def api_powders_insert():
            try:
                j = request.get_json(force=True, silent=True) or {}
                self.db.insert_powder(
                    int(j["powder_id"]),
                    str(j["powder_name"]),
                    str(j["cas_number"]),
                    float(j["bulk_density"]),
                    str(j["flowability"]),
                    str(j["status"]),
                )
                return jsonify({"ok": True})
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 400

        @app.route("/api/powders/delete", methods=["POST"])
        def api_powders_delete():
            j = request.get_json(force=True, silent=True) or {}
            self.db.delete_powder(int(j["powder_id"]))
            return jsonify({"ok": True})
        
        @app.route("/api/spatulas/insert", methods=["POST"])
        def api_spatulas_insert():
            j = request.get_json(force=True, silent=True) or {}
            self.db.insert_spatula(
                int(j["slot_id"]),
                str(j["spatula_name"]).strip(),
                float(j["sdepth_mm"]),
                float(j["slength_mm"]),
                float(j["volumes_ml"]),
                float(j["retention_default_theta"]),
                float(j["spatula_length_mm"])
            )
            return jsonify({"ok": True})

        @app.route("/api/spatulas/delete", methods=["POST"])
        def api_spatulas_delete():
            j = request.get_json(force=True, silent=True) or {}
            self.db.delete_spatula(int(j["slot_id"]))
            return jsonify({"ok": True})
                
        # datacode Registry CRUD + API 
        @app.route("/datacode_registry", methods=["GET"])
        def datacode_registry_page():
            search = request.args.get("search", "").strip()
            message = request.args.get("message", "").strip()
            category = request.args.get("category", "").strip()

            entries = self.db.fetch_all_datacode_entries(search=search)

            return render_template(
                "datacode_registry.html",
                search=search,
                entries=entries,
                message=message,
                category=category,
                edit_entry=None,
            )


        @app.route("/datacode_registry/edit/<datacode_id>", methods=["GET"])
        def datacode_registry_edit_page(datacode_id: str):
            search = request.args.get("search", "").strip()
            message = request.args.get("message", "").strip()
            category = request.args.get("category", "").strip()

            entries = self.db.fetch_all_datacode_entries(search=search)
            edit_entry = self.db.fetch_datacode_entry(datacode_id)

            if not edit_entry:
                return redirect(
                    url_for(
                        "datacode_registry_page",
                        message=f"{datacode_id} not found",
                        category="error",
                        search=search,
                    )
                )

            return render_template(
                "datacode_registry.html",
                search=search,
                entries=entries,
                message=message,
                category=category,
                edit_entry=edit_entry,
            )


        @app.route("/api/datacode_registry", methods=["GET"])
        def api_datacode_registry_list():
            search = request.args.get("search", "").strip()
            return jsonify(self.db.fetch_all_datacode_entries(search=search))


        @app.route("/api/datacode_registry/<datacode_id>", methods=["GET"])
        def api_datacode_registry_get(datacode_id: str):
            row = self.db.fetch_datacode_entry(datacode_id)
            if not row:
                return jsonify({"status": "error", "message": f"{datacode_id} not found"}), 404
            return jsonify({"status": "success", "data": row})


        @app.route("/api/datacode_registry/create", methods=["POST"])
        def api_datacode_registry_create():
            try:
                if request.is_json:
                    data = request.get_json(force=True) or {}
                else:
                    data = self._datacode_form_to_data(request.form)

                self.db.create_datacode_entry(**data)

                if request.is_json:
                    return jsonify({"status": "success", "message": f'{data["datacode_id"]} created successfully'})

                return redirect(
                    url_for(
                        "datacode_registry_page",
                        message=f'{data["datacode_id"]} created successfully',
                        category="success"
                    )
                )
            except Exception as e:
                if request.is_json:
                    return jsonify({"status": "error", "message": str(e)}), 400

                return redirect(
                    url_for(
                        "datacode_registry_page",
                        message=f"Create failed: {str(e)}",
                        category="error"
                    )
                )


        @app.route("/api/datacode_registry/update/<datacode_id>", methods=["POST", "PUT"])
        def api_datacode_registry_update(datacode_id: str):
            try:
                if request.is_json:
                    data = request.get_json(force=True) or {}
                else:
                    data = self._datacode_form_to_data(request.form)

                self.db.update_datacode_entry(
                    datacode_id=datacode_id,
                    container_id=data.get("container_id"),
                    powder_id=data.get("powder_id"),
                    powder_name=data.get("powder_name", ""),
                    container_type=data.get("container_type", ""),
                    status=data.get("status", "active"),
                    notes=data.get("notes", ""),
                )

                if request.is_json:
                    return jsonify({"status": "success", "message": f"{datacode_id} updated successfully"})

                return redirect(
                    url_for(
                        "datacode_registry_page",
                        message=f"{datacode_id} updated successfully",
                        category="success"
                    )
                )
            except Exception as e:
                if request.is_json:
                    return jsonify({"status": "error", "message": str(e)}), 400

                return redirect(
                    url_for(
                        "datacode_registry_page",
                        message=f"Update failed: {str(e)}",
                        category="error"
                    )
                )


        @app.route("/api/datacode_registry/delete/<datacode_id>", methods=["POST", "DELETE"])
        def api_datacode_registry_delete(datacode_id: str):
            try:
                self.db.delete_datacode_entry(datacode_id)

                if request.method == "DELETE" or request.is_json:
                    return jsonify({"status": "success", "message": f"{datacode_id} deleted successfully"})

                return redirect(
                    url_for(
                        "datacode_registry_page",
                        message=f"{datacode_id} deleted successfully",
                        category="success"
                    )
                )
            except Exception as e:
                if request.method == "DELETE" or request.is_json:
                    return jsonify({"status": "error", "message": str(e)}), 400

                return redirect(
                    url_for(
                        "datacode_registry_page",
                        message=f"Delete failed: {str(e)}",
                        category="error"
                    )
                )
                    
        @app.route("/data")
        def get_data():
            active_slot = self.visualizer.recipe.current_slot_index

            if active_slot is None:
                log_file = self.logger.default_log_file
            else:
                log_file = self.logger.get_log_path(active_slot)
            
            if not os.path.isfile(log_file):
                message = f"Log file not found: {log_file}. Please add the file."
                app.logger.warning(message)
                return jsonify({"error": message}), 404

            df = pd.read_csv(log_file)
            if "spatula" not in df.columns:
                df["spatula"] = ["N/A"] * len(df)
            
            s = self.visualizer.current_session
            return jsonify(
                {
                    "timestamps": df.get("timestamp", []).tolist()[-150:],
                    "weights": df.get("weight_g", []).tolist()[-150:],
                    "spatulas": df.get("spatula", []).tolist()[-150:],
                    "powder": s.powder_name,

                    "target": s.target_weight,

                    "remaining": s.remaining_weight,

                    "spatula": s.spatula_type,

                    "scoop_target": s.spatula_target_qty,

                    "level": s.container_level,

                    "controller": s.controller_name,

                    "state": s.session_state
                    
                }
            )

        @app.route("/session")
        def get_session():

            s = self.visualizer.current_session

            return jsonify(
                {
                    "state": s.session_state,
                    "mode": s.dosing_mode,
                    "controller": s.controller_name,

                    "weight": s.latest_weight,
                    "target": s.target_weight,
                    "remaining": s.remaining_weight,

                    "powder": s.powder_name,
                    "powder_id": s.powder_id,

                    "container": s.container_id,
                    "shape": s.container_shape,
                    "level": s.container_level,

                    "spatula": s.spatula_type,
                    "scoop_target": s.spatula_target_qty,
                    "final_weight": s.final_weight,
                    "error": s.absolute_error,
                    "completion": s.completion_percent  
                }
            )

        @app.route("/scoops")
        def get_scoops():
            """Return live per-scoop accuracy metrics for the active dosing run."""

            records = self.visualizer.current_session.scoop_results
            masses_by_spatula = {}
            for record in records:
                masses_by_spatula.setdefault(record["spatula"], []).append(
                    record["actual_dosed"]
                )

            response = []
            for record in records:
                target = record["scoop_target"]
                actual = record["actual_dosed"]
                masses = masses_by_spatula[record["spatula"]]
                mean_mass = statistics.fmean(masses)
                rsd = (
                    statistics.stdev(masses) / mean_mass * 100.0
                    if len(masses) > 1 and mean_mass != 0.0
                    else None
                )
                response.append(
                    {
                        **record,
                        "relative_error": ((actual - target) / target * 100.0)
                        if target else None,
                        "accuracy": (actual / target * 100.0) if target else None,
                        "rsd": rsd,
                    }
                )

            return jsonify({"scoops": response})
        
        @app.route("/recipe")
        def get_recipe():
            return jsonify(
                {
                    "labels": self.visualizer.recipe.powder_labels,
                    "init_total": self.visualizer.recipe.init_total,
                    "init_percent": self.visualizer.recipe.init_percent,
                    "init_weight": self.visualizer.recipe.init_weight,
                    "final_total": self.visualizer.recipe.final_total,
                    "final_percent": self.visualizer.recipe.final_percent,
                    "final_weight": self.visualizer.recipe.final_weight,
                    "percent_error": self.visualizer.recipe.percent_error,
                }
            )
        
    def run(self) -> None:
        self.app.run(self.host, self.port, debug=False)

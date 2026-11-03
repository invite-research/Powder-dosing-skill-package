import csv
import json
import os
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from statistics import fmean, stdev
from typing import Any, Optional

class WeightLogger:
    def __init__(
        self,
        default_log_file: str,
        validation_log_directory: str,
        dashboard_export_directory: str,
        enable_validation_exports: bool,
    ):
        self.default_log_file = default_log_file
        self.validation_log_directory = Path(validation_log_directory)
        self.dashboard_export_directory = Path(dashboard_export_directory)
        self.last_spatula = "N/A"
        self.enable_validation_exports = enable_validation_exports

    def get_log_path(self, slot_index: Optional[int]) -> str:
        if slot_index == 0:
            return "powder_A_log.csv"
        if slot_index == 1:
            return "powder_B_log.csv"
        if slot_index == 2:
            return "powder_C_log.csv"
        return self.default_log_file

    def ensure_log_header(self, path: str) -> None:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            with open(path, "w", newline="") as f:
                csv.writer(f).writerow(["timestamp", "weight_g", "spatula"])
            print(f"Created new log file with header → {path}")

    def append_live_weight(self, slot_index: Optional[int], weight: float, spatula: str) -> None:
        if weight <= 0.0:
            return

        path = self.get_log_path(slot_index)
        self.ensure_log_header(path)

        if spatula == "N/A" and self.last_spatula != "N/A":
            spatula = self.last_spatula
        elif spatula != "N/A":
            self.last_spatula = spatula

        ts = datetime.now().isoformat(timespec="seconds")
        with open(path, "a", newline="") as f:
            csv.writer(f).writerow([ts, f"{weight:.3f}", spatula])

        print(f"[LOG:{os.path.basename(path)}] {ts} → {weight:.3f} g ({spatula})")

    def start_new_session(self, slot_index):

        path = self.get_log_path(slot_index)

        with open(path, "w", newline="") as f:

            csv.writer(f).writerow(
                ["timestamp","weight_g","spatula"]
            )

        print(f"[LOG] Started new session → {path}")

    def export_validation_log(self,*,container_id: Optional[int],powder_flowability: str,powder_id: Optional[int],
                              powder_level: float,target_weight: float,dosed_weight: float,number_of_scoops: int,) -> Path:
        """Write one immutable validation record for a completed dosing run."""
        if not self.enable_validation_exports:
            return None
        self.validation_log_directory.mkdir(parents=True, exist_ok=True)
        container_name = str(container_id) if container_id not in (None, 0) else "unknown"
        powder_name = str(powder_id) if powder_id not in (None, 0) else "unknown"
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S_%f")
        path = self.validation_log_directory / f"validation_{container_name}_{powder_name}_{timestamp}.csv"

        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f,fieldnames=["container_id","powder_flowability","powder_id","powder_level","target_weight","dosed_weight","number_of_scoops",],)
            writer.writeheader()
            writer.writerow({"container_id": container_id or "",
                             "powder_flowability": powder_flowability,
                             "powder_id": powder_id or "",
                             "powder_level": f"{powder_level:.3f}",
                             "target_weight": f"{target_weight:.3f}",
                             "dosed_weight": f"{dosed_weight:.3f}",
                             "number_of_scoops": number_of_scoops,})

        print(f"[VALIDATION] Exported completed dosing log → {path}")
        return path

    @staticmethod
    def _sanitize_name(value: str) -> str:
        cleaned = "".join(character if character.isalnum() or character in ("-", "_") else "_" for character in value.strip())
        return cleaned or "unknown"

    @staticmethod
    def _read_live_log(log_path: Path) -> list[dict[str, str]]:
        if not log_path.exists():
            return []

        with log_path.open(newline="") as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    def _parse_timestamp(value: str) -> datetime | None:
        if not value:
            return None

        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _build_scoop_metrics(self, scoop_results: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        detailed_rows: list[dict[str, Any]] = []
        grouped_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for record in scoop_results:
            spatula = str(record.get("spatula") or "N/A").strip() or "N/A"
            target = float(record.get("scoop_target") or 0.0)
            actual = float(record.get("actual_dosed") or 0.0)
            relative_error = ((actual - target) / target * 100.0) if target else None
            accuracy = (actual / target * 100.0) if target else None

            detailed_row = {
                "scoop_number": int(record.get("scoop_number") or len(detailed_rows) + 1),
                "spatula": spatula,
                "scoop_target": target,
                "actual_dosed": actual,
                "relative_error": relative_error,
                "accuracy": accuracy,
            }
            detailed_rows.append(detailed_row)
            grouped_rows[spatula.upper()].append(detailed_row)

        grouped_summary: list[dict[str, Any]] = []
        for _spatula_key, rows in grouped_rows.items():
            actuals = [row["actual_dosed"] for row in rows]
            targets = [row["scoop_target"] for row in rows]
            relative_errors = [row["relative_error"] for row in rows if row["relative_error"] is not None]
            accuracies = [row["accuracy"] for row in rows if row["accuracy"] is not None]
            mean_actual = fmean(actuals) if actuals else 0.0
            std_dev = stdev(actuals) if len(actuals) > 1 else None
            rsd = (std_dev / mean_actual * 100.0) if std_dev is not None and mean_actual != 0.0 else None

            grouped_summary.append(
                {
                    "spatula": rows[0]["spatula"],
                    "scoop_count": len(rows),
                    "mean_target": fmean(targets) if targets else 0.0,
                    "mean_actual_dosed": mean_actual,
                    "std_dev_actual_dosed": std_dev,
                    "rsd": rsd,
                    "mean_relative_error": fmean(relative_errors) if relative_errors else None,
                    "mean_accuracy": fmean(accuracies) if accuracies else None,
                }
            )

        return detailed_rows, grouped_summary

    @staticmethod
    def _fmt_number(value: float | None, digits: int = 3) -> str:
        if value is None:
            return "--"
        return f"{value:.{digits}f}"

    @staticmethod
    def _map_range(value: float, domain_min: float, domain_max: float, range_min: float, range_max: float) -> float:
        if domain_max == domain_min:
            return (range_min + range_max) / 2.0
        ratio = (value - domain_min) / (domain_max - domain_min)
        return range_min + ratio * (range_max - range_min)

    def _write_svg_dosing_chart(
        self,
        output_path: Path,
        *,
        timestamps: list[datetime],
        weights: list[float],
        spatulas: list[str],
        target_weight: float,
        level_value: float,
        powder_name: str,
        container_id: Any,
        spatula_colors: dict[str, str],
    ) -> None:
        width, height = 1500, 800
        left, right, top, bottom = 90, 150, 80, 100
        plot_w = width - left - right
        plot_h = height - top - bottom

        lines: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect x="0" y="0" width="100%" height="100%" fill="#0f1523"/>',
            f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#111827" stroke="#334155"/>',
            f'<text x="{left}" y="42" fill="#ffd34e" font-size="26" font-family="Segoe UI, Arial">Completed dosing chart</text>',
            f'<text x="{left}" y="66" fill="#cbd5e1" font-size="15" font-family="Segoe UI, Arial">Powder: {escape(str(powder_name or "UNKNOWN"))} | Container: {escape(str(container_id or "unknown"))}</text>',
        ]

        if not timestamps or not weights:
            lines.extend(
                [
                    f'<text x="{left + plot_w / 2:.1f}" y="{top + plot_h / 2:.1f}" text-anchor="middle" fill="#e5e7eb" font-size="20" font-family="Segoe UI, Arial">No live dosing samples were captured.</text>',
                    "</svg>",
                ]
            )
            output_path.write_text("\n".join(lines), encoding="utf-8")
            return

        y_min = min(min(weights), target_weight)
        y_max = max(max(weights), target_weight)
        if y_max == y_min:
            y_min -= 0.5
            y_max += 0.5
        else:
            pad = (y_max - y_min) * 0.1
            y_min -= pad
            y_max += pad

        x_min = 0
        x_max = max(len(weights) - 1, 1)

        for i in range(6):
            y_val = y_min + (y_max - y_min) * i / 5.0
            y = self._map_range(y_val, y_min, y_max, top + plot_h, top)
            lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" stroke="#334155" stroke-width="1"/>')
            lines.append(f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" fill="#cbd5e1" font-size="13" font-family="Segoe UI, Arial">{self._fmt_number(y_val, 2)} g</text>')

        for i in range(3):
            idx = int(round(i * (len(weights) - 1) / 2.0))
            x = self._map_range(idx, x_min, x_max, left, left + plot_w)
            label = timestamps[idx].strftime("%H:%M:%S")
            lines.append(f'<line x1="{x:.2f}" y1="{top + plot_h}" x2="{x:.2f}" y2="{top + plot_h + 6}" stroke="#cbd5e1"/>')
            lines.append(f'<text x="{x:.2f}" y="{top + plot_h + 26}" text-anchor="middle" fill="#cbd5e1" font-size="13" font-family="Segoe UI, Arial">{label}</text>')

        target_y = self._map_range(target_weight, y_min, y_max, top + plot_h, top)
        lines.append(f'<line x1="{left}" y1="{target_y:.2f}" x2="{left + plot_w}" y2="{target_y:.2f}" stroke="#dc3545" stroke-width="2" stroke-dasharray="8 6"/>')

        level_y = self._map_range(level_value, 0.0, 100.0, top + plot_h, top)
        lines.append(f'<line x1="{left}" y1="{level_y:.2f}" x2="{left + plot_w}" y2="{level_y:.2f}" stroke="#20c997" stroke-width="2" stroke-dasharray="4 4"/>')
        lines.append(f'<text x="{left + plot_w + 12}" y="{top + 4}" fill="#cbd5e1" font-size="13" font-family="Segoe UI, Arial">Level axis (%)</text>')
        for pct in (0, 25, 50, 75, 100):
            py = self._map_range(float(pct), 0.0, 100.0, top + plot_h, top)
            lines.append(f'<text x="{left + plot_w + 12}" y="{py + 4:.2f}" fill="#94a3b8" font-size="12" font-family="Segoe UI, Arial">{pct}</text>')

        for idx in range(1, len(weights)):
            x1 = self._map_range(idx - 1, x_min, x_max, left, left + plot_w)
            y1 = self._map_range(weights[idx - 1], y_min, y_max, top + plot_h, top)
            x2 = self._map_range(idx, x_min, x_max, left, left + plot_w)
            y2 = self._map_range(weights[idx], y_min, y_max, top + plot_h, top)
            color = spatula_colors.get((spatulas[idx - 1] or "N/A").upper(), "#6c757d")
            lines.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="2.6"/>')

        legend_spatulas: list[str] = []
        for spatula in spatulas:
            normalized = (spatula or "N/A").upper()
            if normalized not in legend_spatulas:
                legend_spatulas.append(normalized)
        legend_items = legend_spatulas + ["TARGET_WEIGHT", "CONTAINER_LEVEL"]
        lx = left + plot_w - 280
        legend_height = 30 + len(legend_items) * 22
        ly = top + (plot_h - legend_height) / 2.0 + 18
        lines.append(f'<rect x="{lx - 10}" y="{ly - 18}" width="290" height="{30 + len(legend_items) * 22}" fill="#0b1220" stroke="#334155" rx="8"/>')
        lines.append(f'<text x="{lx}" y="{ly}" fill="#e5e7eb" font-size="14" font-family="Segoe UI, Arial">Legend</text>')
        for i, item in enumerate(legend_items):
            row_y = ly + 18 + i * 22
            if item == "TARGET_WEIGHT":
                color = "#dc3545"
                label = "Target weight"
            elif item == "CONTAINER_LEVEL":
                color = "#20c997"
                label = "Container level"
            else:
                color = spatula_colors.get(item, "#6c757d")
                label = item
            lines.append(f'<rect x="{lx}" y="{row_y - 10}" width="14" height="14" fill="{color}" rx="2"/>')
            lines.append(f'<text x="{lx + 22}" y="{row_y + 1}" fill="#cbd5e1" font-size="13" font-family="Segoe UI, Arial">{escape(label)}</text>')

        lines.extend([f'<text x="{left}" y="{height - 20}" fill="#94a3b8" font-size="12" font-family="Segoe UI, Arial">Export generated by ROX dashboard exporter</text>', "</svg>"])
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def _write_svg_scoop_chart(
        self,
        output_path: Path,
        *,
        detailed_rows: list[dict[str, Any]],
    ) -> None:
        width, height = 1500, 800
        left, right, top, bottom = 90, 60, 80, 160
        plot_w = width - left - right
        plot_h = height - top - bottom

        lines: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect x="0" y="0" width="100%" height="100%" fill="#0f1523"/>',
            f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#111827" stroke="#334155"/>',
            f'<text x="{left}" y="42" fill="#ffd34e" font-size="26" font-family="Segoe UI, Arial">Scoop target vs actual</text>',
        ]

        if not detailed_rows:
            lines.extend(
                [
                    f'<text x="{left + plot_w / 2:.1f}" y="{top + plot_h / 2:.1f}" text-anchor="middle" fill="#e5e7eb" font-size="20" font-family="Segoe UI, Arial">No scoop records were captured.</text>',
                    "</svg>",
                ]
            )
            output_path.write_text("\n".join(lines), encoding="utf-8")
            return

        max_mass = max(max(float(row["scoop_target"]) for row in detailed_rows), max(float(row["actual_dosed"]) for row in detailed_rows), 0.1)
        y_min, y_max = 0.0, max_mass * 1.2

        for i in range(6):
            y_val = y_min + (y_max - y_min) * i / 5.0
            y = self._map_range(y_val, y_min, y_max, top + plot_h, top)
            lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" stroke="#334155" stroke-width="1"/>')
            lines.append(f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" fill="#cbd5e1" font-size="13" font-family="Segoe UI, Arial">{self._fmt_number(y_val, 2)} g</text>')

        pair_count = len(detailed_rows)
        pair_w = plot_w / max(pair_count, 1)
        bar_w = min(26.0, max(pair_w * 0.34, 12.0))

        for i, row in enumerate(detailed_rows):
            base_x = left + pair_w * i + pair_w / 2.0
            target = float(row["scoop_target"])
            actual = float(row["actual_dosed"])
            target_h = top + plot_h - self._map_range(target, y_min, y_max, top + plot_h, top)
            actual_h = top + plot_h - self._map_range(actual, y_min, y_max, top + plot_h, top)

            target_y = top + plot_h - target_h
            actual_y = top + plot_h - actual_h
            lines.append(f'<rect x="{base_x - bar_w - 2:.2f}" y="{target_y:.2f}" width="{bar_w:.2f}" height="{target_h:.2f}" fill="#ffd34e"/>')
            lines.append(f'<rect x="{base_x + 2:.2f}" y="{actual_y:.2f}" width="{bar_w:.2f}" height="{actual_h:.2f}" fill="#20c997"/>')

            label = f"S{row['scoop_number']} {row['spatula']}"
            lines.append(f'<text x="{base_x:.2f}" y="{top + plot_h + 24}" text-anchor="middle" fill="#cbd5e1" font-size="12" font-family="Segoe UI, Arial">{escape(label)}</text>')

        lx = left + plot_w - 240
        ly = top + 20
        lines.append(f'<rect x="{lx - 10}" y="{ly - 18}" width="250" height="70" fill="#0b1220" stroke="#334155" rx="8"/>')
        lines.append(f'<text x="{lx}" y="{ly}" fill="#e5e7eb" font-size="14" font-family="Segoe UI, Arial">Legend</text>')
        lines.append(f'<rect x="{lx}" y="{ly + 14}" width="14" height="14" fill="#ffd34e" rx="2"/>')
        lines.append(f'<text x="{lx + 22}" y="{ly + 26}" fill="#cbd5e1" font-size="13" font-family="Segoe UI, Arial">Scoop target</text>')
        lines.append(f'<rect x="{lx}" y="{ly + 36}" width="14" height="14" fill="#20c997" rx="2"/>')
        lines.append(f'<text x="{lx + 22}" y="{ly + 48}" fill="#cbd5e1" font-size="13" font-family="Segoe UI, Arial">Actual dosed</text>')

        lines.extend([f'<text x="{left}" y="{height - 20}" fill="#94a3b8" font-size="12" font-family="Segoe UI, Arial">Export generated by ROX dashboard exporter</text>', "</svg>"])
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def export_dashboard_bundle(
        self,
        *,
        live_log_path: str | Path,
        session_snapshot: dict[str, Any],
        scoop_results: list[dict[str, Any]],
        validation_log_path: str | Path | None = None,
    ) -> Path:
        """Create a folder of chart images and export files for one finished dosing session."""
        if not self.enable_validation_exports:
            return None
        live_path = Path(live_log_path)
        export_root = self.validation_log_directory / self.dashboard_export_directory
        export_root.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S_%f")
        container_name = self._sanitize_name(str(session_snapshot.get("container_id") or "unknown"))
        powder_name = self._sanitize_name(str(session_snapshot.get("powder_name") or "unknown"))
        bundle_dir = export_root / f"dashboard_{container_name}_{powder_name}_{timestamp}"
        bundle_dir.mkdir(parents=True, exist_ok=True)

        detailed_rows, grouped_summary = self._build_scoop_metrics(scoop_results)
        live_rows = self._read_live_log(live_path)

        spatula_colors = {
            "SPATULA_L": "#007bff",
            "SPATULA_M": "#ff9800",
            "SPATULA_S": "#28a745",
            "SPATULA_FLAT_M": "#9c27b0",
            "SPATULA_FLAT_S": "#e91e63",
            "N/A": "#6c757d",
        }

        timestamps = []
        weights = []
        spatulas = []
        for row in live_rows:
            parsed_timestamp = self._parse_timestamp(row.get("timestamp", ""))
            if parsed_timestamp is None:
                continue
            try:
                weight = float(row.get("weight_g", 0.0))
            except ValueError:
                continue
            timestamps.append(parsed_timestamp)
            weights.append(weight)
            spatulas.append(str(row.get("spatula") or "N/A").strip() or "N/A")

        target_weight = float(session_snapshot.get("target_weight") or 0.0)
        level_value = float(session_snapshot.get("container_level") or 0.0)

        self._write_svg_dosing_chart(
            bundle_dir / "dosing_chart.svg",
            timestamps=timestamps,
            weights=weights,
            spatulas=spatulas,
            target_weight=target_weight,
            level_value=level_value,
            powder_name=str(session_snapshot.get("powder_name") or "UNKNOWN"),
            container_id=session_snapshot.get("container_id") or "unknown",
            spatula_colors=spatula_colors,
        )
        self._write_svg_scoop_chart(bundle_dir / "scoop_chart.svg", detailed_rows=detailed_rows)

        scoop_metrics_path = bundle_dir / "scoop_metrics.csv"
        with scoop_metrics_path.open("w", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["scoop_number", "spatula", "scoop_target", "actual_dosed", "relative_error", "accuracy"],
            )
            writer.writeheader()
            writer.writerows(detailed_rows)

        scoop_summary_path = bundle_dir / "scoop_summary_by_spatula.csv"
        with scoop_summary_path.open("w", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "spatula",
                    "scoop_count",
                    "mean_target",
                    "mean_actual_dosed",
                    "std_dev_actual_dosed",
                    "rsd",
                    "mean_relative_error",
                    "mean_accuracy",
                ],
            )
            writer.writeheader()
            writer.writerows(grouped_summary)

        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "session": session_snapshot,
            "validation_log_path": str(validation_log_path) if validation_log_path else None,
            "live_log_path": str(live_path),
            "files": {
                "dosing_chart": "dosing_chart.svg",
                "scoop_chart": "scoop_chart.svg",
                "scoop_metrics": "scoop_metrics.csv",
                "scoop_summary_by_spatula": "scoop_summary_by_spatula.csv",
            },
        }
        with (bundle_dir / "manifest.json").open("w", newline="") as handle:
            json.dump(manifest, handle, indent=2)

        report_html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>Dashboard export</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #0f1523; color: #f5f5f5; }}
    h1, h2 {{ color: #ffd34e; }}
    img {{ max-width: 100%; border: 1px solid rgba(255,255,255,.15); border-radius: 12px; margin-bottom: 18px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
    th, td {{ border-bottom: 1px solid rgba(255,255,255,.15); padding: 8px 10px; text-align: left; }}
  </style>
</head>
<body>
  <h1>Dashboard export</h1>
  <p>Container {session_snapshot.get('container_id', 'unknown')} / powder {session_snapshot.get('powder_name', 'UNKNOWN')}</p>
  <h2>Dosing chart</h2>
    <img src=\"dosing_chart.svg\" alt=\"Completed dosing chart\">
  <h2>Scoop chart</h2>
    <img src=\"scoop_chart.svg\" alt=\"Scoop target vs actual chart\">
</body>
</html>
"""
        (bundle_dir / "report.html").write_text(report_html, encoding="utf-8")

        print(f"[VALIDATION] Dashboard export bundle → {bundle_dir}")
        return bundle_dir

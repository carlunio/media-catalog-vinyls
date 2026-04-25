from datetime import datetime
from pathlib import Path

from ..config import EXPORTS_DIR
from . import vinilos

COLUMNS = [
    "id",
    "tipo_articulo",
    "nombre",
    "artista",
    "año",
    "sello",
    "pais",
    "duracion_total",
    "estimated_weight",
    "generos",
    "estilos",
    "estado_conservacion",
    "precio",
    "estado_carga",
    "estado_stock",
    "tracklist",
    "notas",
]


def export_vinilos_txt(output_path: Path | None = None):
    rows = vinilos.list_all_full()
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = EXPORTS_DIR / f"vinilos_{timestamp}.txt"

    lines = []
    lines.append("\t".join(COLUMNS))

    for r in rows:
        values = []
        for col in COLUMNS:
            val = r.get(col, "")
            if val is None:
                val = ""
            val = str(val).replace("\t", " ").replace("\n", "\\n")
            values.append(val)

        lines.append("\t".join(values))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "path": output_path,
        "filename": output_path.name,
        "rows": len(rows),
        "columns": COLUMNS,
    }

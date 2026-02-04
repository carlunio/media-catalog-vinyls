from pathlib import Path

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


def export_vinilos_txt(output_path: Path):
    rows = vinilos.list_all_full()

    lines = []
    lines.append("\t".join(COLUMNS))  # cabecera

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

    return output_path

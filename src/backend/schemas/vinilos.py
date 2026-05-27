from pydantic import BaseModel


class ViniloListItem(BaseModel):
    id: str
    nombre: str | None = None


class ViniloUpdateRequest(BaseModel):
    tipo_articulo: str | None
    nombre: str | None
    artista: str | None
    año: int | float | str | None
    sello: str | None
    pais: str | None
    duracion_total: str | None
    estimated_weight: int | float | None
    generos: str | None
    estilos: str | None
    tracklist: str | None
    creditos: str | None
    estado_disco: str | None
    estado_funda: str | None
    comentarios_estado: str | None
    estado_tc: str | None
    precio: int | float | None
    estado_carga: str | None
    estado_stock: str | None
    notas: str | None
    tc_section: str | int | float | None


class ViniloOut(BaseModel):
    id: str
    tipo_articulo: str | None = None
    nombre: str | None = None
    artista: str | None = None
    año: int | None = None
    sello: str | None = None
    pais: str | None = None
    duracion_total: str | None = None
    estimated_weight: float | None = None
    generos: str | None = None
    estilos: str | None = None
    creditos: str | None = None
    estado_disco: str | None = None
    estado_funda: str | None = None
    comentarios_estado: str | None = None
    estado_tc: str | None = None
    menor_precio: float | None = None
    precio: float | None = None
    estado_carga: str | None = None
    estado_stock: str | None = None
    tracklist: str | None = None
    notas: str | None = None
    tc_section: str | None = None
    discogs_image_url: str | None = None


class ExportUploadRequest(BaseModel):
    ids: list[str]

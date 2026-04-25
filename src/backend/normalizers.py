def normalizar_año(valor):
    if valor is None:
        return None

    if isinstance(valor, bool):
        return None

    if isinstance(valor, int):
        return valor if valor > 0 else None

    if isinstance(valor, float):
        if valor.is_integer() and int(valor) > 0:
            return int(valor)
        return None

    if isinstance(valor, str):
        valor = valor.strip()
        if len(valor) >= 4 and valor[:4].isdigit():
            year = int(valor[:4])
            return year if year > 0 else None

    return None

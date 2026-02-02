def normalizar_año(valor):
    if valor is None:
        return None

    if isinstance(valor, int):
        return valor

    if isinstance(valor, str):
        valor = valor.strip()
        if len(valor) >= 4 and valor[:4].isdigit():
            return int(valor[:4])

    return None
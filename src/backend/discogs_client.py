from functools import lru_cache

import discogs_client

from .config import DISCOGS_TOKEN, DISCOGS_USER_AGENT


class DiscogsClientConfigurationError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_client():
    if not DISCOGS_TOKEN:
        raise DiscogsClientConfigurationError(
            "Falta la variable de entorno DISCOGS_TOKEN para usar Discogs"
        )

    return discogs_client.Client(DISCOGS_USER_AGENT, user_token=DISCOGS_TOKEN)

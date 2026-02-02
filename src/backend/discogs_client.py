import discogs_client
from .config import DISCOGS_TOKEN

def get_client():
    return discogs_client.Client(
        "MiCatalogoVinilos/1.0",
        user_token=DISCOGS_TOKEN
    )

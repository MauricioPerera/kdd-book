import requests

from config import STRIPE_KEY


def listar_clientes():
    return requests.get(
        "https://api.stripe.com/v1/customers",
        auth=(STRIPE_KEY, ""),
    )

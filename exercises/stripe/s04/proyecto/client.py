import requests

STRIPE_KEY = "REEMPLAZAR_CON_ENV"


def obtener_cliente(cliente_id):
    return requests.get(
        "https://api.stripe.com/v1/customers/{}".format(cliente_id),
        auth=(STRIPE_KEY, ""),
    )

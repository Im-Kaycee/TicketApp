import requests
from django.conf import settings

PAYSTACK_BASE_URL = "https://api.paystack.co"

HEADERS = {
    "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    "Content-Type": "application/json",
}


def get_banks():
    """
    Fetch list of Nigerian banks from Paystack.
    Returns a list of {name, code} dicts to populate a dropdown during onboarding.
    """
    response = requests.get(
        f"{PAYSTACK_BASE_URL}/bank?currency=NGN",
        headers=HEADERS,
    )
    response.raise_for_status()
    return [
        {"name": bank["name"], "code": bank["code"]}
        for bank in response.json()["data"]
    ]


def create_subaccount(*, business_name, bank_code, account_number, percentage_charge):
    """
    Register an organizer's bank account as a Paystack subaccount.
    Called once during onboarding. Returns the subaccount code to store on the user.
    """
    payload = {
        "business_name": business_name,
        "settlement_bank": bank_code,
        "account_number": account_number,
        "percentage_charge": percentage_charge,
    }

    response = requests.post(
        f"{PAYSTACK_BASE_URL}/subaccount",
        json=payload,
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()["data"]["subaccount_code"]


def initialize_transaction(*, email, amount_naira, reference, subaccount_code, platform_fee_percent):
    """
    Start a payment session. Returns a payment URL to redirect the user to.
    Called when a user purchases tickets.
    """
    amount_kobo = int(amount_naira * 100)

    payload = {
        "email": email,
        "amount": amount_kobo,
        "reference": str(reference),
        "subaccount": subaccount_code,
        "bearer": "account",
        "transaction_charge": int(amount_kobo * (platform_fee_percent / 100)),
    }

    response = requests.post(
        f"{PAYSTACK_BASE_URL}/transaction/initialize",
        json=payload,
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()["data"]


def verify_transaction(reference):
    """
    Independently verify a transaction status directly with Paystack.
    Called inside the webhook to confirm payment actually succeeded.
    Never trust the webhook payload alone — always verify.
    """
    response = requests.get(
        f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()["data"]
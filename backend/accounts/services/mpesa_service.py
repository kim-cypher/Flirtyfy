"""
Safaricom M-Pesa Daraja API integration — STK Push ("Lipa na M-Pesa Online").

IMPORTANT — this cannot process a real payment until you provide real
credentials and a reachable callback URL:
  - MPESA_CONSUMER_KEY / MPESA_CONSUMER_SECRET / MPESA_SHORTCODE / MPESA_PASSKEY
    come from a Daraja app at https://developer.safaricom.co.ke (sandbox apps
    are free and instant; production requires Safaricom approval).
  - MPESA_CALLBACK_URL must be a publicly reachable HTTPS URL. Safaricom's
    servers cannot reach localhost — use ngrok (or similar) in dev, your real
    domain in production.

Defaults to the Daraja SANDBOX environment (MPESA_ENV=sandbox). Switch to
MPESA_ENV=production only once you have production credentials.
"""
import base64
import logging
import datetime
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_SANDBOX_BASE = 'https://sandbox.safaricom.co.ke'
_PRODUCTION_BASE = 'https://api.safaricom.co.ke'


def _base_url():
    return _PRODUCTION_BASE if settings.MPESA_ENV == 'production' else _SANDBOX_BASE


def get_access_token() -> str:
    url = f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    resp = requests.get(
        url,
        auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()['access_token']


def _password_and_timestamp():
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


def normalize_phone(phone: str) -> str:
    """Converts common Kenyan phone formats (07XX..., +2547XX..., 2547XX...) to 2547XXXXXXXX."""
    phone = phone.strip().replace(' ', '').replace('-', '')
    if phone.startswith('+'):
        phone = phone[1:]
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif phone.startswith('7') or phone.startswith('1'):
        phone = '254' + phone
    return phone


def initiate_stk_push(phone_number: str, amount, account_reference: str = 'Flirtyfy') -> dict:
    """
    Triggers an STK push payment prompt to the user's phone.
    Returns the Daraja response dict (includes CheckoutRequestID) on success.
    Raises requests.HTTPError / requests.RequestException on failure —
    callers must catch this (missing/invalid credentials, network issues,
    Safaricom downtime all surface this way).
    """
    phone = normalize_phone(phone_number)
    token = get_access_token()
    password, timestamp = _password_and_timestamp()

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": str(int(amount)),
        "PartyA": phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": "Flirtyfy credits top-up",
    }

    resp = requests.post(
        f"{_base_url()}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def parse_callback(data: dict) -> dict:
    """
    Parses the Daraja STK callback payload (the POST body Safaricom sends to
    MPESA_CALLBACK_URL) into a flat dict:
      {checkout_request_id, merchant_request_id, success, result_desc,
       receipt_number, amount}
    """
    callback = data.get('Body', {}).get('stkCallback', {})
    result_code = callback.get('ResultCode')
    parsed = {
        'checkout_request_id': callback.get('CheckoutRequestID'),
        'merchant_request_id': callback.get('MerchantRequestID'),
        'success': result_code == 0,
        'result_desc': callback.get('ResultDesc', ''),
        'receipt_number': '',
        'amount': None,
    }
    if parsed['success']:
        items = callback.get('CallbackMetadata', {}).get('Item', [])
        values = {item.get('Name'): item.get('Value') for item in items}
        parsed['receipt_number'] = values.get('MpesaReceiptNumber', '')
        parsed['amount'] = values.get('Amount')
    return parsed

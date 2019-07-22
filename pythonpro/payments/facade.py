from datetime import datetime
from typing import Tuple

import pagarme as _pagarme
from dateutil.relativedelta import MO, TH, relativedelta
from django.conf import settings
from django.utils.timezone import now

_pagarme.authentication_key(settings.PAGARME_API_KEY)
PYTOOLS_PRICE = 9999


def pytools_capture(token: str):
    return _pagarme.transaction.capture(token, {'amount': PYTOOLS_PRICE})


class PagarmeValidationException(Exception):
    pass


class PagarmeNotPaidTransaction(Exception):
    pass


def confirm_boleto_payment(user_id, notification: dict, raw_post: str, expected_signature):
    transaction = extract_transaction(notification, raw_post, expected_signature)
    item_id = transaction['items'][0]['id']
    # id is generated concatenating Module slug and user's id. Check content_client_landing_page pagarme JS
    expected_id = f'pytools-{user_id}'
    if item_id != expected_id:
        raise PagarmeValidationException(f"Expected item's id {expected_id} differs from {item_id}", notification)
    return transaction


def extract_transaction(notification: dict, raw_post: str, expected_signature):
    if not _pagarme.postback.validate(expected_signature, raw_post):
        raise PagarmeValidationException(notification, expected_signature)
    if notification['object'] != 'transaction' or notification['current_status'] != 'paid':
        raise PagarmeNotPaidTransaction()
    return _pagarme.transaction.find_by_id(notification['transaction[id]'])


def calculate_pytools_promotion_interval() -> Tuple[datetime, datetime]:
    """
    calculate promotion interval for this week based on time. Promotion will begin on monday and stop on Thursday
    :return:
    """
    now_dt = now()
    this_week_monday = now_dt + relativedelta(weekday=MO(-1), hour=0, minute=0, second=0)
    this_week_thursday = this_week_monday + relativedelta(weekday=TH, hour=23, minute=59, second=59)
    return this_week_monday, this_week_thursday


def is_on_pytools_promotion_season(creation: datetime) -> bool:
    """
    Calculate if is period of promotion which is 7 weeks after creation
    :param creation: datetime of creation
    :return: boolean indication if its os promotion period or not
    """
    promotion_begin, _ = calculate_pytools_promotion_interval()
    creation_begin = promotion_begin + relativedelta(weekday=MO(-8))
    creation_end = creation_begin + relativedelta(days=6, hour=23, minute=59, second=59)
    return creation_begin <= creation <= creation_end

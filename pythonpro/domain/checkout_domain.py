# Setup django pagarme listener
from celery import shared_task
from django_pagarme import facade as django_pagarme_facade

from pythonpro.core import facade as core_facade
from pythonpro.domain import user_facade
from pythonpro.email_marketing import facade as email_marketing_facade


def contact_info_listener(name, email, phone, payment_item_slug, user=None):
    if (user is not None) and user.is_authenticated:
        user_id = user.id
        if 'pytools' in payment_item_slug:
            core_facade.client_checkout_form(user, 'unknown')
        elif 'membership' in payment_item_slug:
            core_facade.member_checkout_form(user)
    else:
        user_id = None
    email_marketing_facade.create_or_update_with_no_role.delay(
        name, email, f'{payment_item_slug}-form', id=user_id, phone=str(phone)
    )


django_pagarme_facade.add_contact_info_listener(contact_info_listener)


def user_factory(pagarme_transaction):
    customer = pagarme_transaction['customer']
    customer_email = customer['email'].lower()
    customer_first_name = customer['name'].split()[0]
    return user_facade.force_register_lead(customer_first_name, customer_email)


django_pagarme_facade.set_user_factory(user_factory)


@shared_task()
def payment_handler_task(payment_id):
    payment = django_pagarme_facade.find_payment(payment_id)
    status = payment.status()
    if status == django_pagarme_facade.PAID:
        slug = payment.first_item_slug()
        if 'pytools' in slug:
            user_facade.promote_client(payment.user, 'unknow')
        elif 'membership' in slug:
            user_facade.promote_member(payment.user, 'unknow')
        else:
            raise ValueError(f'{slug} should contain pytools or membership')


def payment_change_handler(payment_id):
    payment_handler_task.delay(payment_id)


django_pagarme_facade.add_payment_status_changed(payment_change_handler)

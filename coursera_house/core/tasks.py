from __future__ import absolute_import, unicode_literals
from celery import task

from ..settings import EMAIL_HOST, EMAIL_PORT, EMAIL_RECEPIENT

from .models import Setting

from django.core.mail import send_mail

from .views import get_controllers_state, send_controllers_state, get_user


@task()
def smart_home_manager():
    # Здесь ваш код для проверки условий
    states = get_controllers_state()
    send_data = {}

    if states['leak_detector']:
        if states['cold_water']:
            send_data.update({'cold_water': False})
            states['cold_water'] = False
        if states['hot_water']:
            send_data.update({'hot_water': False})
        # user = get_user()
        subject = 'АВАРИЯ'
        message = 'Обнаружена протечка!'

        send_mail(
            subject=subject,
            message=message,
            from_email=EMAIL_RECEPIENT,
            recipient_list=[EMAIL_RECEPIENT]
        )

    if not states['cold_water']:
        if states['boiler']:
            send_data.update({'boiler': False})
        if states['washing_machine'] == 'on':
            send_data.update({'washing_machine': 'off'})
    else:
        if not states['smoke_detector']:
            hot_water_target_temperature = Setting.objects.get(
                controller_name='hot_water_target_temperature'
            ).value

            if states['boiler_temperature'] < (hot_water_target_temperature * 0.9):
                if not states['boiler']:
                    send_data.update({'boiler': True})

            if states['boiler_temperature'] > (hot_water_target_temperature * 1.1):
                if states['boiler']:
                    send_data.update({'boiler': False})

    if states['smoke_detector']:
        if states['air_conditioner']:
            send_data.update({'air_conditioner': False})
        if states['bedroom_light']:
            send_data.update({'bedroom_light': False})
        if states['bathroom_light']:
            send_data.update({'bathroom_light': False})
        if states['boiler']:
            send_data.update({'boiler': False})
        if states['washing_machine'] == 'on':
            send_data.update({'washing_machine': 'off'})
    else:
        bedroom_target_temperature = Setting.objects.get(
            controller_name='bedroom_target_temperature'
        ).value

        if states['bedroom_temperature'] < (bedroom_target_temperature * 0.9):
            if states['air_conditioner']:
                send_data.update({'air_conditioner': False})

        if states['bedroom_temperature'] > (bedroom_target_temperature * 1.1):
            if not states['air_conditioner']:
                send_data.update({'air_conditioner': True})

    if states['curtains'] != 'slightly_open':
        if states['bedroom_light'] or states['outdoor_light'] > 50:
            if states['curtains'] == 'open':
                send_data.update({'curtains': 'close'})
        if not states['bedroom_light'] and states['outdoor_light'] < 50:
            if states['curtains'] == 'close':
                send_data.update({'curtains': 'open'})

    if send_data:
        send_controllers_state(send_data)

    return

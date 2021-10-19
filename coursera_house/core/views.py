from django.urls import reverse_lazy
from django.views.generic import FormView
from django.http import HttpResponse

from .models import Setting
from .form import ControllerForm

from ..settings import SMART_HOME_ACCESS_TOKEN, SMART_HOME_API_URL
import requests
from json.decoder import JSONDecodeError

CONTROLLERS_NAME = {
    'air_conditioner': {'name': 'Кондиционер', 'true': 'вкл', 'false': 'выкл'},
    'bedroom_temperature': {'name': 'Температура в спальне'},
    'bedroom_light': {'name': 'Лампа в спальне',
                      'true': 'вкл', 'false': 'выкл'},
    'smoke_detector': {'name': 'Датчик задымления на потолке',
                       'true': 'задымление', 'false': 'нет'},
    'bedroom_presence': {'name': 'Датчик присутствия в спальне',
                         'true': 'есть человек', 'false': 'нет'},
    'bedroom_motion': {'name': 'Датчик движения в спальне',
                       'true': 'есть движение', 'false': 'нет'},
    'curtains': {'name': 'Занавески', 'open': 'открыты ',
                 'close': 'закрыты', 'slightly_open': 'приоткрыты вручную'},
    'outdoor_light': {'name': 'Датчик освещенности за окном'},
    'boiler': {'name': 'Бойлер', 'true': 'вкл', 'false': 'выкл'},
    'boiler_temperature': {'name': 'Температура горячей воды бойлере'},
    'cold_water': {'name': 'Входной кран холодной воды',
                   'true': 'открыт', 'false': 'закрыт'},
    'hot_water': {'name': 'Входной кран горячей воды',
                  'true': 'открыт', 'false': 'закрыт'},
    'bathroom_light': {'name': 'Лампа в ванной',
                       'true': 'вкл', 'false': 'выкл'},
    'bathroom_presence': {'name': 'Датчик присутствия в ванной',
                          'true': 'есть человек', 'false': 'нет'},
    'bathroom_motion': {'name': 'Датчик движения в ванной',
                        'true': 'есть движение', 'false': 'нет'},
    'washing_machine': {'name': 'Стиральная машина',
                        'on': 'вкл', 'off': 'выкл', 'broken': 'сломана'},
    'leak_detector': {'name': 'Датчик протечки воды',
                      'true': 'протечка', 'false': 'сухо'}
}


def get_user():
    url = 'https://smarthome.webpython.graders.eldf.ru/api/auth.current'
    headers = {
        'Authorization': f'Bearer {SMART_HOME_ACCESS_TOKEN}'
    }
    # try:
    responce = requests.get(
        url,
        headers=headers
    ).json()
    # except requests.exceptions.ConnectionError:
    #     raise requests.exceptions.HTTPError
    result = responce['data']
    return result


def get_controllers_state():
    headers = {
        'Authorization': f'Bearer {SMART_HOME_ACCESS_TOKEN}'
    }
    try:
        responce = requests.get(
            SMART_HOME_API_URL,
            headers=headers
        )
    except requests.exceptions.BaseHTTPError:
        return {}
    if responce.status_code != 200:
        return {}
    result = {}
    try:
        responce = responce.json()
    except JSONDecodeError:
        return {}
    for item in responce['data']:
        result.update({item['name']: item['value']})
    return result


def send_controllers_state(states):
    headers = {
        'Authorization': f'Bearer {SMART_HOME_ACCESS_TOKEN}'
    }
    data = {
        'controllers': []
    }
    for key, value in states.items():
        data['controllers'].append({
            'name': key,
            'value': value
        })
    try:
        responce = requests.post(
            SMART_HOME_API_URL,
            headers=headers,
            json=data
        )
    except requests.exceptions.BaseHTTPError:
        return 'err'

    if responce.status_code != 200:
        return 'err'
    return 'ok'


class ControllerView(FormView):
    form_class = ControllerForm
    template_name = 'core/control.html'
    success_url = reverse_lazy('form')
    states = {}

    def get(self, request, *args, **kwargs):
        self.states = get_controllers_state()
        if not self.states:
            return HttpResponse(status=502)
        return super().get(request)

    def post(self, request, *args, **kwargs):
        if request == 'err':
            return HttpResponse(status=502)
        return super().post(request)

    def get_context_data(self, **kwargs):
        context = super(ControllerView, self).get_context_data()
        context['data'] = {}
        for controller, state in self.states.items():
            if controller == 'boiler_temperature':
                if self.states['cold_water'] is False:
                    state = 'null'
            context['data'].update(
                {
                    controller:
                    state
                }
            )

        return context

    def get_initial(self):
        try:
            bedroom_target_temperature = Setting.objects.get(
                controller_name='bedroom_target_temperature'
            )
        except Setting.DoesNotExist:
            bedroom_target_temperature = Setting(
                controller_name='bedroom_target_temperature',
                label='Желаемая температура в спальне',
                value=21
            )
            bedroom_target_temperature.save()
        try:
            hot_water_target_temperature = Setting.objects.get(
                controller_name='hot_water_target_temperature'
            )
        except Setting.DoesNotExist:
            hot_water_target_temperature = Setting(
                controller_name='hot_water_target_temperature',
                label='Желаемая температура горячей воды',
                value=80
            )
            hot_water_target_temperature.save()
        result = {
            'bedroom_target_temperature': bedroom_target_temperature.value,
            'hot_water_target_temperature': hot_water_target_temperature.value,
            'bedroom_light': self.states.get('bedroom_light'),
            'bathroom_light': self.states.get('bathroom_light')
        }
        return result

    def form_valid(self, form):
        states = get_controllers_state()
        send_data = {}
        if not states['smoke_detector']:
            if states['bedroom_light'] != form.cleaned_data['bedroom_light']:
                send_data.update(
                    {'bedroom_light': form.cleaned_data['bedroom_light']}
                )

            if states['bathroom_light'] != form.cleaned_data['bathroom_light']:
                send_data.update(
                    {'bathroom_light': form.cleaned_data['bathroom_light']}
                )

        if send_data:
            if send_controllers_state(send_data) == 'err':
                self.post('err')

        bedroom_target_temperature = Setting.objects.get(
                controller_name='bedroom_target_temperature'
            )

        if bedroom_target_temperature.value !=\
           form.cleaned_data['bedroom_target_temperature']:
            bedroom_target_temperature.value =\
                form.cleaned_data['bedroom_target_temperature']
            bedroom_target_temperature.save()

        hot_water_target_temperature = Setting.objects.get(
                controller_name='hot_water_target_temperature'
            )

        if hot_water_target_temperature.value !=\
           form.cleaned_data['hot_water_target_temperature']:
            hot_water_target_temperature.value =\
                form.cleaned_data['hot_water_target_temperature']
            hot_water_target_temperature.save()

        return super(ControllerView, self).form_valid(form)

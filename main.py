import logging
import requests
import threading
import time

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction

logger = logging.getLogger(__name__)

CACHE_TEMPO = 300  # 5 minutos

class OndeEstouExtension(Extension):

    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.cache = None
        self.cache_timestamp = 0


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):

        # Se tiver cache válido, usa
        if extension.cache and (time.time() - extension.cache_timestamp < CACHE_TEMPO):
            return RenderResultListAction(extension.cache)

        # Senão, busca em background
        threading.Thread(
            target=self.buscar_localizacao,
            args=(extension,),
            daemon=True
        ).start()

        return RenderResultListAction([
            ExtensionResultItem(
                icon='map-marker',
                name='🔎 Obtendo localização...',
                description='Aguarde um instante',
                on_enter=HideWindowAction()
            )
        ])

    def buscar_localizacao(self, extension):

        headers = {
            "User-Agent": "Ulauncher-OndeEstou"
        }

        apis = [
            "https://ipapi.co/json/",
            "http://ip-api.com/json/"
        ]

        data = None

        for url in apis:
            try:
                response = requests.get(url, headers=headers, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    break
            except Exception as e:
                logger.warning(f"Falha na API {url}: {e}")

        if not data:
            items = [
                ExtensionResultItem(
                    icon='error',
                    name='❌ Não foi possível obter localização',
                    description='Verifique sua conexão',
                    on_enter=HideWindowAction()
                )
            ]
            extension.publish_event(RenderResultListAction(items))
            return

        # Normalização dos dados (suporta duas APIs)
        cidade = data.get('city', 'Desconhecida')
        regiao = data.get('region') or data.get('regionName', 'Desconhecida')
        pais = data.get('country_name') or data.get('country', 'Desconhecido')
        ip = data.get('ip') or data.get('query', 'Desconhecido')
        latitude = data.get('latitude') or data.get('lat', '')
        longitude = data.get('longitude') or data.get('lon', '')

        localizacao = f"{cidade}, {regiao}, {pais}"

        items = [
            ExtensionResultItem(
                icon='map-marker',
                name=f'📍 {localizacao}',
                description=f'IP: {ip} | Enter copia',
                on_enter=CopyToClipboardAction(localizacao)
            ),
            ExtensionResultItem(
                icon='globe',
                name='Coordenadas aproximadas',
                description=f'Lat: {latitude}, Lon: {longitude}',
                on_enter=CopyToClipboardAction(f"{latitude}, {longitude}")
            )
        ]

        if latitude and longitude:
            maps_url = f"https://www.google.com/maps?q={latitude},{longitude}"
            items.append(
                ExtensionResultItem(
                    icon='maps',
                    name='Abrir no Google Maps',
                    description='Visualizar no mapa',
                    on_enter=OpenUrlAction(maps_url)
                )
            )

        # Salva cache
        extension.cache = items
        extension.cache_timestamp = time.time()

        # Atualiza interface
        extension.publish_event(RenderResultListAction(items))


if __name__ == '__main__':
    OndeEstouExtension().run()

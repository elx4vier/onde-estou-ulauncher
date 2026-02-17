import logging
import requests
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction

logger = logging.getLogger(__name__)

class OndeEstouExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())

class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        items = []
        
        try:
            # Timeout reduzido para 2 segundos (evita espera longa)
            response = requests.get('https://ipapi.co/json/', timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                
                cidade = data.get('city', 'Desconhecida')
                regiao = data.get('region', 'Desconhecida')
                pais = data.get('country_name', 'Desconhecido')
                ip = data.get('ip', 'Desconhecido')
                latitude = data.get('latitude', '')
                longitude = data.get('longitude', '')
                
                localizacao = f"{cidade}, {regiao}, {pais}"
                
                # Item principal
                items.append(ExtensionResultItem(
                    icon='map-marker',
                    name=f'📍 {localizacao}',
                    description=f'IP: {ip} | Enter copia localização',
                    on_enter=CopyToClipboardAction(localizacao)
                ))
                
                # Coordenadas
                items.append(ExtensionResultItem(
                    icon='globe',
                    name='Coordenadas aproximadas',
                    description=f'Lat: {latitude}, Lon: {longitude} | Enter copia',
                    on_enter=CopyToClipboardAction(f"{latitude}, {longitude}")
                ))
                
                # Google Maps
                if latitude and longitude:
                    maps_url = f"https://www.google.com/maps?q={latitude},{longitude}"
                    items.append(ExtensionResultItem(
                        icon='maps',
                        name='Abrir no Google Maps',
                        description='Clique para ver no mapa',
                        on_enter=OpenUrlAction(maps_url)
                    ))
            else:
                # Erro HTTP (ex: 429, 500)
                items.append(ExtensionResultItem(
                    icon='error',
                    name='Erro na API',
                    description=f'Código HTTP {response.status_code}',
                    on_enter=HideWindowAction()
                ))
                
        except requests.exceptions.Timeout:
            logger.error("Timeout na consulta à API")
            items.append(ExtensionResultItem(
                icon='error',
                name='Tempo limite excedido',
                description='A API demorou muito para responder',
                on_enter=HideWindowAction()
            ))
        except requests.exceptions.ConnectionError:
            logger.error("Erro de conexão")
            items.append(ExtensionResultItem(
                icon='error',
                name='Sem conexão',
                description='Verifique sua internet',
                on_enter=HideWindowAction()
            ))
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            items.append(ExtensionResultItem(
                icon='error',
                name='Erro inesperado',
                description='Não foi possível obter localização',
                on_enter=HideWindowAction()
            ))
        
        # Sempre retorna algo (nunca fica vazio)
        return RenderResultListAction(items)

if __name__ == '__main__':
    OndeEstouExtension().run()

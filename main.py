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
            # Consulta à API ipapi.co (não requer chave, limite 1000/dia)
            response = requests.get('https://ipapi.co/json/', timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                cidade = data.get('city', 'Desconhecida')
                regiao = data.get('region', 'Desconhecida')
                pais = data.get('country_name', 'Desconhecido')
                codigo_pais = data.get('country_code', '')
                ip = data.get('ip', 'Desconhecido')
                latitude = data.get('latitude', '')
                longitude = data.get('longitude', '')
                
                localizacao = f"{cidade}, {regiao}, {pais}"
                
                # Item principal: localização
                items.append(ExtensionResultItem(
                    icon='map-marker',
                    name=f'📍 {localizacao}',
                    description=f'IP: {ip} | Enter copia a localização',
                    on_enter=CopyToClipboardAction(localizacao)
                ))
                
                # Item secundário: coordenadas
                items.append(ExtensionResultItem(
                    icon='globe',
                    name='Coordenadas aproximadas',
                    description=f'Lat: {latitude}, Lon: {longitude} | Enter copia as coordenadas',
                    on_enter=CopyToClipboardAction(f"{latitude}, {longitude}")
                ))
                
                # Item para abrir no Google Maps (se tiver coordenadas)
                if latitude and longitude:
                    maps_url = f"https://www.google.com/maps?q={latitude},{longitude}"
                    items.append(ExtensionResultItem(
                        icon='maps',
                        name='Abrir no Google Maps',
                        description='Clique para ver a localização aproximada no mapa',
                        on_enter=OpenUrlAction(maps_url)
                    ))
            else:
                items.append(ExtensionResultItem(
                    icon='error',
                    name='Erro na consulta',
                    description=f'Código HTTP {response.status_code}',
                    on_enter=HideWindowAction()
                ))
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão: {e}")
            items.append(ExtensionResultItem(
                icon='error',
                name='Erro de conexão',
                description='Verifique sua internet',
                on_enter=HideWindowAction()
            ))
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            items.append(ExtensionResultItem(
                icon='error',
                name='Erro inesperado',
                description='Ocorreu um erro interno',
                on_enter=HideWindowAction()
            ))
        
        return RenderResultListAction(items)

if __name__ == '__main__':
    OndeEstouExtension().run()

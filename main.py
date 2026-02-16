import gi
gi.require_version('Geoclue', '2.0')
from gi.repository import Geoclue, GLib
import requests
from threading import Thread

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.OpenAction import OpenAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

class WhereAmI(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        # Mostra um item de carregamento; ao pressionar Enter, inicia a busca
        data = {'query': event.get_argument() or ''}
        return RenderResultListAction([
            ExtensionResultItem(
                icon='images/icon.png',
                name='Obtendo localização...',
                description='Pressione Enter para buscar sua cidade',
                on_enter=ExtensionCustomAction(data, keep_app_open=True)
            )
        ])

class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()
        # Inicia a busca em uma thread separada para não travar a interface
        Thread(target=self._buscar_localizacao, args=(extension,)).start()
        # Fecha a janela enquanto processa (será reaberta com os resultados)
        return HideWindowAction()

    def _buscar_localizacao(self, extension):
        try:
            # Conecta ao Geoclue
            cliente = Geoclue.Simple.new_sync(
                "ulauncher.whereami",
                Geoclue.AccuracyLevel.EXACT,
                None, None
            )
            loc = cliente.get_location()
            if not loc:
                raise Exception("Não foi possível obter localização")

            lat = loc.get_property('latitude')
            lon = loc.get_property('longitude')
            if not lat or not lon:
                raise Exception("Coordenadas não disponíveis")

            # Geocodificação reversa com Nominatim
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
            headers = {'User-Agent': 'UlauncherWhereAmI/1.0'}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code != 200:
                raise Exception("Falha na geocodificação")

            dados = resp.json()
            cidade = (dados.get('address', {}).get('city') or
                      dados.get('address', {}).get('town') or
                      dados.get('address', {}).get('village') or
                      dados.get('address', {}).get('county'))
            if not cidade:
                raise Exception("Cidade não encontrada nos dados")

            # Prepara os resultados
            resultados = [
                ExtensionResultItem(
                    icon='images/icon.png',
                    name=f"📍 Você está em: {cidade}",
                    description="Clique para copiar o nome da cidade",
                    on_enter=CopyToClipboardAction(cidade)
                ),
                ExtensionResultItem(
                    icon='images/icon.png',
                    name="🌐 Abrir no Google Maps",
                    description="Ver localização no mapa",
                    on_enter=OpenAction(f"https://www.google.com/maps?q={lat},{lon}")
                )
            ]
            # Atualiza a janela com os resultados (na thread principal)
            GLib.idle_add(extension.window.show_results,
                          RenderResultListAction(resultados))

        except Exception as e:
            print(f"Erro na extensão WhereAmI: {e}")
            GLib.idle_add(extension.window.show_results,
                          RenderResultListAction([
                              ExtensionResultItem(
                                  icon='images/icon.png',
                                  name="❌ Erro ao obter localização",
                                  description=str(e),
                                  on_enter=HideWindowAction()
                              )
                          ]))

if __name__ == '__main__':
    WhereAmI().run()

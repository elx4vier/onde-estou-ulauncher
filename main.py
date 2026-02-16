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
        # Mostra item de carregamento
        data = {'action': 'start'}
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
        action = data.get('action')
        if action == 'start':
            # Inicia a busca assíncrona da localização (no loop principal)
            extension.location_data = None
            extension.cidade = None
            extension.coordenadas = None
            extension.msg_erro = None

            # Cria cliente Geoclue (síncrono, mas rápido)
            try:
                extension.cliente = Geoclue.Simple.new_sync(
                    "ulauncher.whereami",
                    Geoclue.AccuracyLevel.EXACT,
                    None, None
                )
                # Conecta ao sinal de atualização
                extension.cliente.connect("notify::location", self._on_location_updated, extension)
                # Pede a localização (assíncrono)
                extension.cliente.get_location_async(None, self._on_location_async_ready, extension)
            except Exception as e:
                extension.msg_erro = f"Erro Geoclue: {e}"
                self._mostrar_erro(extension)

            # Fecha a janela enquanto aguarda
            return HideWindowAction()
        elif action == 'mostrar_resultados':
            # Se já temos os dados prontos, exibe
            return self._criar_resultados(data)
        else:
            return HideWindowAction()

    def _on_location_updated(self, simple, pspec, extension):
        """Callback quando a localização é atualizada (pode ser chamado várias vezes)"""
        loc = simple.props.location
        if loc:
            self._processar_localizacao(loc, extension)

    def _on_location_async_ready(self, source, result, extension):
        """Callback após get_location_async"""
        try:
            loc = source.get_location_finish(result)
            if loc:
                self._processar_localizacao(loc, extension)
            else:
                extension.msg_erro = "Localização não disponível"
                self._mostrar_erro(extension)
        except Exception as e:
            extension.msg_erro = f"Erro ao obter localização: {e}"
            self._mostrar_erro(extension)

    def _processar_localizacao(self, loc, extension):
        """Extrai coordenadas e inicia geocodificação em thread"""
        lat = loc.get_property('latitude')
        lon = loc.get_property('longitude')
        if lat and lon:
            extension.coordenadas = (lat, lon)
            # Inicia thread para geocodificação
            Thread(target=self._geocode, args=(lat, lon, extension)).start()
        else:
            extension.msg_erro = "Coordenadas inválidas"
            self._mostrar_erro(extension)

    def _geocode(self, lat, lon, extension):
        """Faz a geocodificação reversa (em thread separada)"""
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
            headers = {'User-Agent': 'UlauncherWhereAmI/1.0'}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                dados = resp.json()
                cidade = (dados.get('address', {}).get('city') or
                          dados.get('address', {}).get('town') or
                          dados.get('address', {}).get('village') or
                          dados.get('address', {}).get('county'))
                if cidade:
                    extension.cidade = cidade
                    # Volta para a thread principal para mostrar resultados
                    GLib.idle_add(self._mostrar_resultados, extension)
                else:
                    extension.msg_erro = "Cidade não encontrada"
                    GLib.idle_add(self._mostrar_erro, extension)
            else:
                extension.msg_erro = f"Erro HTTP {resp.status_code}"
                GLib.idle_add(self._mostrar_erro, extension)
        except Exception as e:
            extension.msg_erro = f"Erro na geocodificação: {e}"
            GLib.idle_add(self._mostrar_erro, extension)

    def _mostrar_resultados(self, extension):
        """Cria a lista de resultados e atualiza a janela"""
        if extension.cidade and extension.coordenadas:
            lat, lon = extension.coordenadas
            resultados = [
                ExtensionResultItem(
                    icon='images/icon.png',
                    name=f"📍 Você está em: {extension.cidade}",
                    description="Clique para copiar o nome da cidade",
                    on_enter=CopyToClipboardAction(extension.cidade)
                ),
                ExtensionResultItem(
                    icon='images/icon.png',
                    name="🌐 Abrir no Google Maps",
                    description="Ver localização no mapa",
                    on_enter=OpenAction(f"https://www.google.com/maps?q={lat},{lon}")
                )
            ]
            extension.window.show_results(RenderResultListAction(resultados))
        else:
            self._mostrar_erro(extension)

    def _mostrar_erro(self, extension):
        """Mostra mensagem de erro"""
        msg = extension.msg_erro or "Erro desconhecido"
        extension.window.show_results(RenderResultListAction([
            ExtensionResultItem(
                icon='images/icon.png',
                name="❌ Erro ao obter localização",
                description=msg,
                on_enter=HideWindowAction()
            )
        ]))

    def _criar_resultados(self, data):
        """Cria resultados a partir dos dados (usado para ação de 'mostrar_resultados')"""
        cidade = data.get('cidade')
        lat = data.get('lat')
        lon = data.get('lon')
        if cidade and lat and lon:
            return RenderResultListAction([
                ExtensionResultItem(
                    icon='images/icon.png',
                    name=f"📍 Você está em: {cidade}",
                    description="Clique para copiar",
                    on_enter=CopyToClipboardAction(cidade)
                ),
                ExtensionResultItem(
                    icon='images/icon.png',
                    name="🌐 Abrir no mapa",
                    description="Ver no Google Maps",
                    on_enter=OpenAction(f"https://www.google.com/maps?q={lat},{lon}")
                )
            ])
        else:
            return RenderResultListAction([
                ExtensionResultItem(
                    icon='images/icon.png',
                    name="❌ Erro",
                    description="Dados incompletos",
                    on_enter=HideWindowAction()
                )
            ])

if __name__ == '__main__':
    WhereAmI().run()

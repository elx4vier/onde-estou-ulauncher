import gi
gi.require_version('Geoclue', '2.0')
from gi.repository import Geoclue, GLib, GObject
import requests

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.OpenAction import OpenAction


class WhereAmI(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        try:
            # Cria cliente Geoclue
            extension.cliente = Geoclue.Simple.new_sync(
                "io.ulauncher.Ulauncher",
                Geoclue.AccuracyLevel.CITY,
                None
            )

            # Conecta ao sinal de mudança de localização
            extension.cliente.connect("notify::location", self._on_location_changed, extension)

            # Inicia a busca
            extension.cliente.start()

            # Timeout de 8 segundos
            GLib.timeout_add_seconds(8, self._timeout, extension)

            # Mensagem inicial
            return RenderResultListAction([
                ExtensionResultItem(
                    icon='images/icon.png',
                    name='🔎 Obtendo sua localização...',
                    description='Aguarde um instante',
                    on_enter=None
                )
            ])

        except Exception as e:
            return RenderResultListAction([
                ExtensionResultItem(
                    icon='images/icon.png',
                    name="❌ Erro ao inicializar Geoclue",
                    description=str(e),
                    on_enter=None
                )
            ])

    def _on_location_changed(self, cliente, pspec, extension):
        loc = cliente.props.location
        if not loc:
            return

        lat = loc.get_property('latitude')
        lon = loc.get_property('longitude')

        if lat is None or lon is None:
            self._mostrar_erro(extension, "Coordenadas inválidas")
            return

        # Para o cliente depois de obter a localização
        cliente.stop()

        # Faz geocodificação reversa
        self._geocode(lat, lon, extension)

    def _geocode(self, lat, lon, extension):
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1"
            headers = {'User-Agent': 'UlauncherWhereAmI/1.0'}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code != 200:
                self._mostrar_erro(extension, f"Erro HTTP {resp.status_code}")
                return

            data = resp.json()
            addr = data.get('address', {})
            cidade = addr.get('city') or addr.get('town') or addr.get('village') or addr.get('county')
            estado = addr.get('state')
            pais = addr.get('country')

            if not cidade or not estado or not pais:
                self._mostrar_erro(extension, "Cidade/Estado/País não encontrados")
                return

            texto = f"{cidade}, {estado} - {pais}"

            extension.window.show_results(RenderResultListAction([
                ExtensionResultItem(
                    icon='images/icon.png',
                    name=f"📍 {texto}",
                    description="Clique para copiar",
                    on_enter=CopyToClipboardAction(texto)
                ),
                ExtensionResultItem(
                    icon='images/icon.png',
                    name="🌐 Abrir no Google Maps",
                    description="Ver localização no mapa",
                    on_enter=OpenAction(f"https://www.google.com/maps?q={lat},{lon}")
                )
            ]))

        except Exception as e:
            self._mostrar_erro(extension, f"Erro na geocodificação: {e}")

    def _mostrar_erro(self, extension, mensagem):
        extension.window.show_results(RenderResultListAction([
            ExtensionResultItem(
                icon='images/icon.png',
                name="❌ Erro ao obter localização",
                description=mensagem,
                on_enter=None
            )
        ]))

    def _timeout(self, extension):
        self._mostrar_erro(extension, "Tempo esgotado ao obter localização")
        return False  # Não repetir


if __name__ == '__main__':
    WhereAmI().run()

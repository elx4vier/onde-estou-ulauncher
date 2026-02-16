import gi
gi.require_version("Geoclue", "2.0")
from gi.repository import Geoclue, GLib
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
    TIMEOUT_SECONDS = 8

    def on_event(self, event, extension):
        try:
            # Cria cliente Geoclue corretamente (3 argumentos)
            client = Geoclue.Simple.new_sync(
                "io.ulauncher.Ulauncher",  # App-id aceito pelo Geoclue
                Geoclue.AccuracyLevel.CITY,  # Suficiente para cidade/estado
                None  # cancellable
            )

            # Pega localização imediatamente
            loc = client.props.location
            if loc is None:
                # Timeout se não tiver localização
                GLib.timeout_add_seconds(self.TIMEOUT_SECONDS,
                                         lambda: self._mostrar_erro(extension, "Localização não disponível"))
                return RenderResultListAction([
                    ExtensionResultItem(
                        icon="images/icon.png",
                        name="🔎 Obtendo localização...",
                        description="Aguarde um instante...",
                        on_enter=None
                    )
                ])

            lat = loc.get_property("latitude")
            lon = loc.get_property("longitude")

            if lat is None or lon is None:
                return self._mostrar_erro(extension, "Coordenadas inválidas")

            # Geocodificação reversa (cidade, estado, país)
            return self._geocode(lat, lon, extension)

        except Exception as e:
            return self._mostrar_erro(extension, f"Erro ao inicializar Geoclue: {e}")

    def _geocode(self, lat, lon, extension):
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1"
            headers = {"User-Agent": "UlauncherWhereAmI/1.0"}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code != 200:
                return self._mostrar_erro(extension, f"Erro HTTP {resp.status_code}")

            data = resp.json()
            addr = data.get("address", {})
            cidade = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county")
            estado = addr.get("state")
            pais = addr.get("country")

            if not cidade or not estado or not pais:
                return self._mostrar_erro(extension, "Cidade/Estado/País não encontrados")

            texto = f"{cidade}, {estado} - {pais}"

            return RenderResultListAction([
                ExtensionResultItem(
                    icon="images/icon.png",
                    name=f"📍 {texto}",
                    description="Clique para copiar",
                    on_enter=CopyToClipboardAction(texto)
                ),
                ExtensionResultItem(
                    icon="images/icon.png",
                    name="🌐 Abrir no Google Maps",
                    description="Ver localização no mapa",
                    on_enter=OpenAction(f"https://www.google.com/maps?q={lat},{lon}")
                )
            ])

        except Exception as e:
            return self._mostrar_erro(extension, f"Erro na geocodificação: {e}")

    def _mostrar_erro(self, extension, mensagem):
        return RenderResultListAction([
            ExtensionResultItem(
                icon="images/icon.png",
                name="❌ Erro ao obter localização",
                description=mensagem,
                on_enter=None
            )
        ])


if __name__ == "__main__":
    WhereAmI().run()

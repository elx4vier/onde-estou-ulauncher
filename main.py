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
    TIMEOUT_MS = 8000  # 8 segundos de timeout

    def on_event(self, event, extension):
        try:
            # Cria cliente Geoclue
            extension.client = Geoclue.Simple.new_sync(
                "io.ulauncher.Ulauncher",
                Geoclue.AccuracyLevel.CITY,
                None
            )

            # Conecta ao sinal notify::location
            extension.client.connect("notify::location", self._on_location_changed, extension)

            # Mensagem inicial
            resultados = [
                ExtensionResultItem(
                    icon="images/icon.png",
                    name="🔎 Obtendo localização...",
                    description="Aguarde um instante",
                    on_enter=None
                )
            ]

            # Timeout para evitar travamento
            GLib.timeout_add(self.TIMEOUT_MS, self._timeout, extension)

            return RenderResultListAction(resultados)

        except Exception as e:
            return RenderResultListAction([
                ExtensionResultItem(
                    icon="images/icon.png",
                    name="❌ Erro ao inicializar Geoclue",
                    description=str(e),
                    on_enter=None
                )
            ])

    def _on_location_changed(self, client, pspec, extension):
        loc = client.props.location
        if not loc:
            return

        lat = loc.get_property("latitude")
        lon = loc.get_property("longitude")

        if lat is None or lon is None:
            self._mostrar_erro(extension, "Coordenadas inválidas")
            return

        # Faz geocodificação reversa
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1"
            headers = {"User-Agent": "UlauncherWhereAmI/1.0"}
            resp = requests.get(url, headers=headers, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            addr = data.get("address", {})

            cidade = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county")
            estado = addr.get("state")
            pais = addr.get("country")

            if not cidade or not estado or not pais:
                self._mostrar_erro(extension, "Cidade/Estado/País não encontrados")
                return

            texto = f"{cidade}, {estado} - {pais}"

            extension.window.show_results(RenderResultListAction([
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
            ]))

        except Exception as e:
            self._mostrar_erro(extension, f"Erro na geocodificação: {e}")

    def _mostrar_erro(self, extension, mensagem):
        extension.window.show_results(RenderResultListAction([
            ExtensionResultItem(
                icon="images/icon.png",
                name="❌ Erro ao obter localização",
                description=mensagem,
                on_enter=None
            )
        ]))

    def _timeout(self, extension):
        self._mostrar_erro(extension, "Tempo esgotado ao obter localização")
        return False  # Não repetir


if __name__ == "__main__":
    WhereAmI().run()

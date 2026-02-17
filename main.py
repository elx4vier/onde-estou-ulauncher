import requests

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.OpenAction import OpenAction


class WhereAmIIPAPI(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        try:
            # Faz requisição à API ipapi.co
            resp = requests.get("https://ipapi.co/json", timeout=5)
            resp.raise_for_status()
            data = resp.json()

            cidade = data.get("city")
            estado = data.get("region")
            pais = data.get("country_name")
            lat = data.get("latitude")
            lon = data.get("longitude")

            if not cidade or not estado or not pais:
                return self._mostrar_erro(extension, "Cidade/Estado/País não encontrados")

            texto = f"{cidade}, {estado} - {pais}"

            resultados = [
                ExtensionResultItem(
                    icon="images/icon.png",
                    name=f"📍 {texto}",
                    description="Clique para copiar",
                    on_enter=CopyToClipboardAction(texto)
                )
            ]

            # Se lat/lon disponíveis, adiciona link Google Maps
            if lat and lon:
                resultados.append(
                    ExtensionResultItem(
                        icon="images/icon.png",
                        name="🌐 Abrir no Google Maps",
                        description="Ver localização no mapa",
                        on_enter=OpenAction(f"https://www.google.com/maps?q={lat},{lon}")
                    )
                )

            return RenderResultListAction(resultados)

        except Exception as e:
            return self._mostrar_erro(extension, f"Erro ao obter localização: {e}")

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
    WhereAmIIPAPI().run()

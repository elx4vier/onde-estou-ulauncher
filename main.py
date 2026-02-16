import requests

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction


class WhereAmI(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):

        try:
            resp = requests.get("https://ipapi.co/json/", timeout=3)
            data = resp.json()

            cidade = data.get("city")
            estado = data.get("region")
            pais = data.get("country_name")

            if cidade and estado and pais:
                texto = f"{cidade}, {estado} - {pais}"

                return RenderResultListAction([
                    ExtensionResultItem(
                        icon='images/icon.png',
                        name=f"📍 {texto}",
                        description="Pressione Enter para copiar",
                        on_enter=CopyToClipboardAction(texto)
                    )
                ])
            else:
                return RenderResultListAction([
                    ExtensionResultItem(
                        icon='images/icon.png',
                        name="❌ Localização não encontrada",
                        description="Verifique sua conexão",
                        on_enter=None
                    )
                ])

        except Exception as e:
            return RenderResultListAction([
                ExtensionResultItem(
                    icon='images/icon.png',
                    name="❌ Erro ao buscar localização",
                    description=str(e),
                    on_enter=None
                )
            ])


if __name__ == '__main__':
    WhereAmI().run()

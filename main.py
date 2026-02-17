import logging
import requests

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction

logger = logging.getLogger(__name__)


class OndeEstouExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):

        try:
            geo = requests.get("https://ipapi.co/json/", timeout=4).json()

            cidade = geo.get("city", "")
            estado = geo.get("region", "")
            country_code = geo.get("country_code", "").upper()

            # 🔧 Configurações do usuário
            mostrar_estado = extension.preferences.get("mostrar_estado", "sim")
            mostrar_bandeira = extension.preferences.get("mostrar_bandeira", "sim")
            copiar_formato = extension.preferences.get("formato_copia", "cidade_estado_pais")

            # 🇧🇷 Bandeira dinâmica
            def flag(code):
                if len(code) != 2:
                    return ""
                return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)

            bandeira = flag(country_code) if mostrar_bandeira == "sim" else ""

            linha_estado = ""
            if estado and mostrar_estado == "sim":
                linha_estado = f"{estado}\n"

            titulo = "Você está em:\n"

            texto = (
                f"{titulo}\n"
                f"{cidade}\n"
                f"{linha_estado}"
                f"{country_code} {bandeira}"
                f"\n\n"  # 👈 Espaçamento antes das fontes
            )

            rodape = "Fontes: ipapi.co"

            # 📋 Formato de cópia configurável
            if copiar_formato == "cidade":
                copia = cidade
            elif copiar_formato == "cidade_pais":
                copia = f"{cidade}, {country_code}"
            else:
                copia = f"{cidade}, {estado}, {country_code}"

            return RenderResultListAction([
                ExtensionResultItem(
                    icon='map-marker',
                    name=texto,
                    description=rodape,
                    on_enter=CopyToClipboardAction(copia)
                )
            ])

        except Exception as e:
            logger.error(e)

            return RenderResultListAction([
                ExtensionResultItem(
                    icon='dialog-error',
                    name="Erro ao obter localização",
                    description="Verifique sua conexão",
                    on_enter=CopyToClipboardAction("Erro")
                )
            ])


if __name__ == "__main__":
    OndeEstouExtension().run()

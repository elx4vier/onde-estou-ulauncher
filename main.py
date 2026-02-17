import logging
import requests
import threading
import time
import os
import tempfile

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction

logger = logging.getLogger(__name__)

CACHE_TEMPO = 300


class OndeEstouExtension(Extension):

    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.cache = None
        self.cache_timestamp = 0


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):

        if extension.cache and (time.time() - extension.cache_timestamp < CACHE_TEMPO):
            return RenderResultListAction(extension.cache)

        threading.Thread(
            target=self.buscar_dados,
            args=(extension,),
            daemon=True
        ).start()

        return RenderResultListAction([
            ExtensionResultItem(
                icon='map-marker',
                name="Carregando...",
                description="Buscando informações do município",
                on_enter=HideWindowAction()
            )
        ])

    def buscar_dados(self, extension):

        try:
            # 🌍 Localização
            geo = requests.get("https://ipapi.co/json/", timeout=3).json()

            cidade = geo.get("city", "")
            estado = geo.get("region", "")
            country_code = geo.get("country_code", "").upper()

            # 🇧🇷 Bandeira
            def flag(code):
                if len(code) != 2:
                    return ""
                return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)

            bandeira = flag(country_code)

            # 📖 Wikipédia resumo
            resumo = ""
            imagem_path = 'map-marker'

            try:
                wiki = requests.get(
                    f"https://pt.wikipedia.org/api/rest_v1/page/summary/{cidade}",
                    timeout=3
                ).json()

                resumo = wiki.get("extract", "")

                # Baixa imagem se existir
                if "thumbnail" in wiki:
                    img_url = wiki["thumbnail"]["source"]
                    img_data = requests.get(img_url).content

                    tmp_file = os.path.join(
                        tempfile.gettempdir(),
                        f"{cidade}.jpg"
                    )

                    with open(tmp_file, "wb") as f:
                        f.write(img_data)

                    imagem_path = tmp_file

            except:
                resumo = "Resumo não disponível."

            # 📝 Montagem visual

            titulo = "Você está em:\n"
            linha_cidade = f"{cidade}\n"

            linha_estado = ""
            if estado:
                linha_estado = f"{estado}\n"

            linha_pais = f"{country_code} {bandeira}"

            texto = (
                f"{titulo}\n"
                f"{linha_cidade}"
                f"{linha_estado}"
                f"{linha_pais}\n\n"
                f"{resumo}\n\n"
                f"Fontes: ipapi.co • Wikipédia"
            )

            items = [
                ExtensionResultItem(
                    icon=imagem_path,
                    name=texto,
                    description="",
                    on_enter=CopyToClipboardAction(f"{cidade}, {estado}, {country_code}")
                )
            ]

            extension.cache = items
            extension.cache_timestamp = time.time()

            extension.publish_event(RenderResultListAction(items))

        except Exception as e:
            logger.error(e)


if __name__ == "__main__":
    OndeEstouExtension().run()

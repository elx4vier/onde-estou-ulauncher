import logging
import requests
import time
import json
import os
import threading

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action import RenderResultListAction, CopyToClipboardAction

logger = logging.getLogger(__name__)

CACHE_TTL = 300
CACHE_FILE = os.path.expanduser("~/.cache/onde_estou_cache.json")


def create_session():
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=0.3,
                    status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class OndeEstouExtension(Extension):

    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.session = create_session()
        self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.cached_result = None
        self.last_fetch = 0
        self.fetching = False
        self.lock = threading.Lock()

    def icon(self, filename):
        path = os.path.join(self.base_path, "images", filename)
        return path if os.path.exists(path) else ""


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):

        now = time.time()

        # ✅ Se já tem cache válido → retorna instantâneo
        if extension.cached_result and (now - extension.last_fetch < CACHE_TTL):
            return RenderResultListAction([extension.cached_result])

        # 🚀 Se não está buscando ainda → inicia thread
        with extension.lock:
            if not extension.fetching:
                extension.fetching = True
                threading.Thread(
                    target=self.background_fetch,
                    args=(extension,),
                    daemon=True
                ).start()

        # 🔄 Mostra loading temporário
        return RenderResultListAction([
            ExtensionResultItem(
                icon=extension.icon("loading.png"),
                name="Obtendo localização...",
                description="Aguarde alguns instantes..."
            )
        ])

    # ----------------------------------
    # THREAD SEGURA
    # ----------------------------------
    def background_fetch(self, extension):

        try:
            geo = self.fetch_location(extension)

            cidade = geo.get("city", "Desconhecida")
            estado = geo.get("region", "")
            pais = geo.get("country_code", geo.get("countryCode", "")).upper()
            ip = geo.get("ip", geo.get("query", ""))

            bandeira = self.flag(pais)

            texto = (
                "Você está em:\n\n"
                f"{cidade}\n"
                f"{estado}\n"
                f"{pais} {bandeira}\n\n"
                f"IP: {ip}"
            ).strip()

            item = ExtensionResultItem(
                icon=extension.icon("icon.png"),
                name=texto,
                description="Fonte: ipapi.co | ip-api.com",
                on_enter=CopyToClipboardAction(f"{cidade}, {estado}, {pais}")
            )

            extension.cached_result = item
            extension.last_fetch = time.time()

        except Exception as e:

            logger.error(f"Erro async: {e}")

            extension.cached_result = ExtensionResultItem(
                icon=extension.icon("error.png"),
                name="Erro ao obter localização",
                description="Offline ou serviço indisponível",
                on_enter=CopyToClipboardAction("Erro")
            )

        finally:
            with extension.lock:
                extension.fetching = False

    # ----------------------------------
    # Busca API
    # ----------------------------------
    def fetch_location(self, extension):

        try:
            r = extension.session.get("https://ipapi.co/json/", timeout=2)
            return r.json()
        except Exception:
            r = extension.session.get("http://ip-api.com/json/", timeout=2)
            return r.json()

    def flag(self, code):
        if len(code) != 2:
            return ""
        return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)


if __name__ == "__main__":
    OndeEstouExtension().run()

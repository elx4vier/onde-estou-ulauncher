import logging
import requests
import time
import json
import os

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action import RenderResultListAction, CopyToClipboardAction

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutos
CACHE_FILE = os.path.expanduser("~/.cache/onde_estou_cache.json")


def create_session():
    session = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class OndeEstouExtension(Extension):

    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.session = create_session()
        self.cache = None
        self.cache_time = 0

        # 📁 Caminho base da extensão
        self.base_path = os.path.dirname(os.path.abspath(__file__))

    def icon(self, filename):
        path = os.path.join(self.base_path, "images", filename)
        return path if os.path.exists(path) else ""


class KeywordQueryEventListener(EventListener):

    def get_flag(self, code):
        if len(code) != 2:
            return ""
        return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)

    def load_file_cache(self):
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r") as f:
                    data = json.load(f)
                    if time.time() - data["timestamp"] < CACHE_TTL:
                        return data["geo"]
        except Exception:
            pass
        return None

    def save_file_cache(self, geo):
        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump({
                    "timestamp": time.time(),
                    "geo": geo
                }, f)
        except Exception:
            pass

    def fetch_location(self, extension):
        now = time.time()

        if extension.cache and (now - extension.cache_time < CACHE_TTL):
            return extension.cache

        file_cache = self.load_file_cache()
        if file_cache:
            extension.cache = file_cache
            extension.cache_time = now
            return file_cache

        try:
            response = extension.session.get(
                "https://ipapi.co/json/",
                timeout=2
            )
            if response.status_code == 200:
                geo = response.json()
            else:
                raise Exception("API principal falhou")
        except Exception:
            try:
                response = extension.session.get(
                    "http://ip-api.com/json/",
                    timeout=2
                )
                geo = response.json()
            except Exception:
                raise Exception("Todas as APIs falharam")

        extension.cache = geo
        extension.cache_time = now
        self.save_file_cache(geo)

        return geo

    def on_event(self, event, extension):

        # 🔄 Loading imediato
        loading_item = ExtensionResultItem(
            icon=extension.icon("loading.png"),
            name="Obtendo localização...",
            description="Consultando serviço de geolocalização"
        )

        try:
            geo = self.fetch_location(extension)

            cidade = geo.get("city", "Desconhecida")
            estado = geo.get("region", "")
            pais = geo.get("country_code", geo.get("countryCode", "")).upper()
            ip = geo.get("ip", geo.get("query", ""))

            mostrar_estado = extension.preferences.get("mostrar_estado", "sim")
            mostrar_bandeira = extension.preferences.get("mostrar_bandeira", "sim")
            copiar_formato = extension.preferences.get("formato_copia", "cidade_estado_pais")
            mostrar_ip = extension.preferences.get("mostrar_ip", "sim")

            bandeira = self.get_flag(pais) if mostrar_bandeira == "sim" else ""

            linha_estado = f"{estado}\n" if estado and mostrar_estado == "sim" else ""
            linha_ip = f"IP: {ip}\n" if ip and mostrar_ip == "sim" else ""

            texto = (
                "Você está em:\n\n"
                f"{cidade}\n"
                f"{linha_estado}"
                f"{pais} {bandeira}\n\n"
                f"{linha_ip}"
            ).strip()

            rodape = "Fonte: ipapi.co | ip-api.com"

            # 📋 Formato cópia
            if copiar_formato == "cidade":
                copia = cidade
            elif copiar_formato == "cidade_pais":
                copia = f"{cidade}, {pais}"
            elif copiar_formato == "ip":
                copia = ip
            else:
                copia = f"{cidade}, {estado}, {pais}"

            return RenderResultListAction([
                ExtensionResultItem(
                    icon=extension.icon("icon.png"),
                    name=texto,
                    description=rodape,
                    on_enter=CopyToClipboardAction(copia)
                )
            ])

        except Exception as e:
            logger.error(f"Erro localização: {e}")

            return RenderResultListAction([
                ExtensionResultItem(
                    icon=extension.icon("error.png"),
                    name="Erro ao obter localização",
                    description="Offline ou serviço indisponível",
                    on_enter=CopyToClipboardAction("Erro")
                )
            ])


if __name__ == "__main__":
    OndeEstouExtension().run()

import logging
import requests
import time
import os

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutos


# --------------------------------------------------
# 🔥 Session otimizada com retry
# --------------------------------------------------
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

        # 🚀 Performance
        self.session = create_session()
        self.cache = None
        self.cache_time = 0

        # 📁 Caminho base da extensão
        self.base_path = os.path.dirname(os.path.abspath(__file__))

    def icon(self, filename):
        path = os.path.join(self.base_path, "images", filename)
        return path if os.path.exists(path) else ""


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):

        try:
            now = time.time()

            # 🔥 Cache em memória
            if extension.cache and (now - extension.cache_time < CACHE_TTL):
                geo = extension.cache
            else:
                geo = self.fetch_location(extension)
                extension.cache = geo
                extension.cache_time = now

            cidade = geo.get("city", "Desconhecida")
            estado = geo.get("region", "")
            country_code = geo.get("country_code", geo.get("countryCode", "")).upper()
            ip = geo.get("ip", geo.get("query", ""))

            # 🔧 Preferências
            mostrar_estado = extension.preferences.get("mostrar_estado", "sim")
            mostrar_bandeira = extension.preferences.get("mostrar_bandeira", "sim")
            copiar_formato = extension.preferences.get("formato_copia", "cidade_estado_pais")
            mostrar_ip = extension.preferences.get("mostrar_ip", "sim")

            # 🇧🇷 Bandeira dinâmica
            bandeira = self.flag(country_code) if mostrar_bandeira == "sim" else ""

            # 🧱 Layout elegante
            divisor = "────────────"

            linha_estado = f"{estado}\n" if estado and mostrar_estado == "sim" else ""
            linha_ip = f"\n{divisor}\nIP: {ip}" if ip and mostrar_ip == "sim" else ""

            texto = (
                "📍 Localização atual\n\n"
                f"{cidade}\n"
                f"{linha_estado}"
                f"{country_code} {bandeira}"
                f"{linha_ip}"
            )

            rodape = "Fonte: ipapi.co | ip-api.com"

            # 📋 Formato de cópia
            if copiar_formato == "cidade":
                copia = cidade
            elif copiar_formato == "cidade_pais":
                copia = f"{cidade}, {country_code}"
            elif copiar_formato == "ip":
                copia = ip
            else:
                copia = f"{cidade}, {estado}, {country_code}"

            return RenderResultListAction([
                ExtensionResultItem(
                    icon=extension.icon("icon.png"),
                    name=texto.strip(),
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
                    description="Verifique sua conexão",
                    on_enter=CopyToClipboardAction("Erro")
                )
            ])

    # --------------------------------------------------
    # 🌍 Busca com fallback
    # --------------------------------------------------
    def fetch_location(self, extension):

        try:
            r = extension.session.get("https://ipapi.co/json/", timeout=2)
            if r.status_code == 200:
                return r.json()
            raise Exception("API principal falhou")
        except Exception:
            r = extension.session.get("http://ip-api.com/json/", timeout=2)
            return r.json()

    # --------------------------------------------------
    # 🇧🇷 Emoji de bandeira
    # --------------------------------------------------
    def flag(self, code):
        if len(code) != 2:
            return ""
        return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)


if __name__ == "__main__":
    OndeEstouExtension().run()

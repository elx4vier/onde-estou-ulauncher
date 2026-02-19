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

CACHE_TTL = 600  # 10 minutos

def create_session():
    session = requests.Session()
    retries = Retry(total=0, backoff_factor=0.1, status_forcelist=[429, 500, 502, 503, 504])
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
        self.base_path = os.path.dirname(os.path.abspath(__file__))

    def icon(self, filename):
        path = os.path.join(self.base_path, "images", filename)
        if os.path.exists(path):
            return path
        return os.path.join(self.base_path, "images", "icon.png")

class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        try:
            now = time.time()
            # --- Cache em memória ---
            if extension.cache and (now - extension.cache_time < CACHE_TTL):
                geo = extension.cache
            else:
                geo = self.fetch_location(extension)
                extension.cache = geo
                extension.cache_time = now

            # --- Extração de dados ---
            cidade = geo.get("city") or "Desconhecida"
            estado = geo.get("region") or ""
            code = geo.get("country_code") or ""
            ip = geo.get("ip") or "N/A"
            provider = geo.get("provider", "API")

            pais_sigla = code.upper() if code else "??"
            bandeira = self.flag(code)

            # --- Monta o texto final com quebras de linha ---
            linhas = ["Você está em:", "", f"{cidade}"]
            if estado:
                linhas.append(f"{estado}")
            linhas.append(f"{pais_sigla} {bandeira}")
            linhas.append("")  # espaço antes da fonte
            texto_principal = "\n".join(linhas)

            # --- Texto para copiar ---
            copia = f"{cidade}, {estado}, {pais_sigla} (IP: {ip})".replace(", ,", ",")

            return RenderResultListAction([
                ExtensionResultItem(
                    icon=extension.icon("icon.png"),
                    name=texto_principal,
                    description=f"Fonte: {provider} | IP: {ip}",
                    on_enter=CopyToClipboardAction(copia)
                )
            ])

        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            return RenderResultListAction([
                ExtensionResultItem(
                    icon=extension.icon("icon.png"),
                    name="Não foi possível obter a localização.",
                    description="",
                    on_enter=None
                )
            ])

    def fetch_location(self, extension):
        apis = [
            ("https://ip-api.com/json/", "ip-api.com", 2),
            ("https://freeipapi.com/api/json", "freeipapi.com", 2),
            ("https://ipapi.co/json/", "ipapi.co", 2),
            ("https://ipinfo.io/json", "ipinfo.io", 3)
        ]

        for url, name, timeout in apis:
            try:
                logger.info(f"Tentando {name}...")
                r = extension.session.get(url, timeout=timeout)
                if r.status_code != 200:
                    continue
                data = r.json()
                if data.get("status") == "fail" or "error" in data:
                    logger.warning(f"{name} negou a requisição.")
                    continue

                return {
                    "ip": data.get("query") or data.get("ip") or data.get("ipAddress"),
                    "city": data.get("city") or data.get("cityName") or "Desconhecida",
                    "region": data.get("regionName") or data.get("region") or "",
                    "country_name": data.get("country") or data.get("country_name") or "",
                    "country_code": (data.get("countryCode") or data.get("country_code") or "")[:2],
                    "provider": name
                }

            except Exception as e:
                logger.warning(f"Falha na {name}: {e}")
                continue

        # --- Todas APIs falharam ---
        return {"city": "Nenhuma API respondeu", "region": "", "ip": "N/A", "country_name": "??", "country_code": "", "provider": "Nenhuma API respondeu"}

    def flag(self, code):
        if not code or len(code) != 2:
            return ""
        return chr(ord(code[0].upper()) + 127397) + chr(ord(code[1].upper()) + 127397)

if __name__ == "__main__":
    OndeEstouExtension().run()

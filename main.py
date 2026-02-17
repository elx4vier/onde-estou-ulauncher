import requests
import time

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction

# Sua chave Google
GOOGLE_API_KEY = "AIzaSyChY5KA-9Fgzz4o-hvhny0F1YKimAFrbzo"

# Cache de 10 minutos
_last_location = None
_last_timestamp = 0
CACHE_TIMEOUT = 600  # segundos

def extrair_cidade_estado_pais(geo_data):
    """
    Extrai cidade/município, estado e país do JSON do Google Maps,
    ignorando bairros e sublocalidades menores.
    """
    cidade = estado = pais = None
    for result in geo_data.get("results", []):
        for comp in result.get("address_components", []):
            types = comp.get("types", [])
            # Cidade: locality > postal_town > administrative_area_level_2
            if not cidade and any(t in types for t in ["locality", "postal_town", "administrative_area_level_2"]):
                cidade = comp.get("long_name")
            # Estado
            if not estado and "administrative_area_level_1" in types:
                estado = comp.get("long_name")
            # País
            if not pais and "country" in types:
                pais = comp.get("long_name")
        if cidade and estado and pais:
            break
    return cidade, estado, pais


class OndeEstou(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        global _last_location, _last_timestamp

        # Retorna cache se recente
        if _last_location and (time.time() - _last_timestamp) < CACHE_TIMEOUT:
            return RenderResultListAction(_last_location)

        try:
            # 1️⃣ Google Maps Geolocation API
            url_geo = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
            resp = requests.post(url_geo, json={"considerIp": True}, timeout=5)
            resp.raise_for_status()
            geo_data = resp.json()
            loc = geo_data.get("location")
            if not loc:
                return self._mostrar_erro(extension, "Não foi possível obter lat/lon da Geolocation API")
            lat = loc.get("lat")
            lon = loc.get("lng")

            # 2️⃣ Google Maps Geocoding API
            url_rev = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={GOOGLE_API_KEY}"
            resp = requests.get(url_rev, timeout=5)
            resp.raise_for_status()
            geo_data_rev = resp.json()

            cidade, estado, pais = extrair_cidade_estado_pais(geo_data_rev)
            if not cidade or not pais:
                return self._mostrar_erro(extension, "Não foi possível extrair cidade/estado/país")

            texto = f"{cidade}"
            if estado:
                texto += f", {estado}"
            texto += f" — {pais}"

            # Apenas 1 botão: copiar
            itens = [
                ExtensionResultItem(
                    icon="images/icon.png",
                    name=f"📍 {texto}",
                    description="Clique para copiar",
                    on_enter=CopyToClipboardAction(texto)
                )
            ]

            # Atualiza cache
            _last_location = itens
            _last_timestamp = time.time()

            return RenderResultListAction(itens)

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
    OndeEstou().run()

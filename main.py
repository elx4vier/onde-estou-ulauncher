import requests
import time
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.BaseAction import BaseAction

GOOGLE_API_KEY = "AIzaSyChY5KA-9Fgzz4o-hvhny0F1YKimAFrbzo"

_last_location = None
_last_timestamp = 0
CACHE_TIMEOUT = 600  # 10 minutos

ICONE_PADRAO = "images/icon.png"
ICONE_ERRO = "images/error.png"

def extrair_cidade_estado_pais(geo_data):
    cidade = estado = pais = codigo_pais = None
    for result in geo_data.get("results", []):
        for comp in result.get("address_components", []):
            types = comp.get("types", [])
            if not cidade and any(t in types for t in ["locality","postal_town","administrative_area_level_2"]):
                cidade = comp.get("long_name")
            if not estado and "administrative_area_level_1" in types:
                estado = comp.get("long_name")
            if not pais and "country" in types:
                pais = comp.get("long_name")
                codigo_pais = comp.get("short_name")
        if cidade and estado and pais:
            break
    return cidade, estado, pais, codigo_pais

def country_code_to_emoji(code):
    if not code or len(code) != 2:
        return ""
    return chr(ord(code[0].upper()) + 127397) + chr(ord(code[1].upper()) + 127397)

class BuscarLocalizacaoAction(BaseAction):
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key

    def run(self):
        global _last_location, _last_timestamp

        # Usa cache se ainda for válido
        if _last_location and (time.time() - _last_timestamp) < CACHE_TIMEOUT:
            return RenderResultListAction(_last_location)

        try:
            # Obtém coordenadas via geolocalização por IP
            url_geo = f"https://www.googleapis.com/geolocation/v1/geolocate?key={self.api_key}"
            resp = requests.post(url_geo, json={"considerIp": True}, timeout=5)
            resp.raise_for_status()
            loc = resp.json().get("location")
            if not loc:
                return self._mostrar_erro("Não foi possível obter latitude/longitude")

            lat, lon = loc.get("lat"), loc.get("lng")

            # Geocoding reverso para endereço
            url_rev = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={self.api_key}"
            resp = requests.get(url_rev, timeout=5)
            resp.raise_for_status()
            geo_data_rev = resp.json()

            cidade, estado, pais, codigo_pais = extrair_cidade_estado_pais(geo_data_rev)
            if not cidade or not pais:
                return self._mostrar_erro("Não foi possível extrair cidade/estado/país")

            bandeira = country_code_to_emoji(codigo_pais)
            # Formata a descrição com cidade, estado (se houver) e país (apenas sigla)
            local_formatado = f"{cidade}"
            if estado:
                local_formatado += f", {estado}"
            local_formatado += f" — {codigo_pais} {bandeira}"

            # Texto completo para cópia (sem a bandeira)
            texto_completo = f"{cidade}"
            if estado:
                texto_completo += f", {estado}"
            texto_completo += f" — {pais} ({codigo_pais})"

            itens = [
                ExtensionResultItem(
                    icon=ICONE_PADRAO,
                    name="Você está em",
                    description=local_formatado,
                    on_enter=CopyToClipboardAction(texto_completo)
                )
            ]

            # Atualiza cache
            _last_location = itens
            _last_timestamp = time.time()

            return RenderResultListAction(itens)

        except Exception as e:
            return self._mostrar_erro(f"Erro ao obter localização: {e}")

    def _mostrar_erro(self, mensagem):
        return RenderResultListAction([
            ExtensionResultItem(
                icon=ICONE_ERRO,
                name="❌ Erro ao obter localização",
                description=mensagem,
                on_enter=None
            )
        ])

class OndeEstouExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, OndeEstouKeywordListener())

class OndeEstouKeywordListener(EventListener):
    def on_event(self, event, extension):
        # Retorna o item principal da extensão
        item_principal = ExtensionResultItem(
            icon=ICONE_PADRAO,
            name="Onde eu estou",
            description="Exibe sua localização atual",
            on_enter=BuscarLocalizacaoAction(extension.preferences.get("google_api_key", GOOGLE_API_KEY))
        )
        return RenderResultListAction([item_principal])

if __name__ == "__main__":
    OndeEstouExtension().run()

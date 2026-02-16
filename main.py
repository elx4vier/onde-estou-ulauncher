#!/usr/bin/env python3
import gi
gi.require_version('Geoclue', '2.0')
from gi.repository import Geoclue, GLib

from ulauncher.api import Extension, Result
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.OpenAction import OpenAction

class WhereAmI(Extension):
    def __init__(self):
        super().__init__()
        self.location_data = None
        self.main_loop = None

    def on_input(self, input_text: str, trigger_id: str):
        """
        Chamado quando o usuário digita a palavra‑chave.
        Vamos tentar obter a localização e retornar um item com a cidade.
        """
        # Inicia a obtenção da localização de forma assíncrona
        self.location_data = None
        self.main_loop = GLib.MainLoop.new(None, False)

        # Configura o cliente Geoclue
        self.cliente = Geoclue.Simple.new_sync(
            "ulauncher.whereami",   # nome da aplicação
            Geoclue.AccuracyLevel.EXACT,
            None,                   # cancellable
            None                    # error
        )

        if not self.cliente:
            return self._erro("Não foi possível conectar ao Geoclue")

        # Conecta ao sinal de atualização de localização
        self.cliente.connect("notify::location", self._on_location_updated)

        # Pede uma localização (pode chamar o callback imediatamente se já tiver cache)
        self.cliente.get_location_async(None, self._on_location_async_ready, None)

        # Roda o loop principal do GLib até receber a localização (ou timeout)
        GLib.timeout_add_seconds(10, self._timeout)  # timeout de 10s
        self.main_loop.run()

        # Se obtivemos dados, retorna o resultado; senão, erro
        if self.location_data:
            cidade = self._extrair_cidade(self.location_data)
            if cidade:
                return [
                    Result(
                        name=f"📍 Você está em: {cidade}",
                        description="Clique para copiar o nome da cidade",
                        on_enter=CopyToClipboardAction(cidade)
                    ),
                    Result(
                        name="🌐 Abrir no Google Maps",
                        description="Ver localização no mapa",
                        on_enter=OpenAction(
                            f"https://www.google.com/maps?q={self.location_data['latitude']},{self.location_data['longitude']}"
                        )
                    )
                ]
            else:
                return self._erro("Não foi possível determinar a cidade")
        else:
            return self._erro("Tempo limite excedido ao obter localização")

    def _on_location_updated(self, simple, pspec):
        """Callback chamado quando a localização é atualizada"""
        loc = simple.props.location
        if loc:
            self._processar_localizacao(loc)

    def _on_location_async_ready(self, source, result, user_data):
        """Callback após chamada get_location_async"""
        try:
            loc = source.get_location_finish(result)
            if loc:
                self._processar_localizacao(loc)
        except Exception as e:
            print(f"Erro ao obter localização: {e}")

    def _processar_localizacao(self, loc):
        """Extrai latitude e longitude e para o loop principal"""
        lat = loc.get_property('latitude')
        lon = loc.get_property('longitude')
        if lat and lon:
            # Usando geocoder reverso simples (Nominatim) para obter cidade
            # Faremos uma requisição HTTP rápida (em uma thread para não travar)
            from threading import Thread
            import requests

            def obter_cidade():
                try:
                    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
                    headers = {'User-Agent': 'UlauncherWhereAmI/1.0'}
                    resp = requests.get(url, headers=headers, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        cidade = data.get('address', {}).get('city') or \
                                 data.get('address', {}).get('town') or \
                                 data.get('address', {}).get('village') or \
                                 data.get('address', {}).get('county')
                        if cidade:
                            self.location_data = {
                                'cidade': cidade,
                                'latitude': lat,
                                'longitude': lon
                            }
                except Exception as e:
                    print(f"Erro no geocoding: {e}")
                finally:
                    self.main_loop.quit()

            Thread(target=obter_cidade).start()
        else:
            self.main_loop.quit()

    def _timeout(self):
        """Chamado se o tempo limite for atingido"""
        if self.main_loop and self.main_loop.is_running():
            self.main_loop.quit()
        return False  # não repetir

    def _extrair_cidade(self, dados):
        return dados.get('cidade')

    def _erro(self, msg):
        return [Result(name=f"❌ {msg}", description="Tente novamente mais tarde")]

if __name__ == '__main__':
    WhereAmI().run()

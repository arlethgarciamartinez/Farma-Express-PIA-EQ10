"""Bus de eventos en memoria: despacha Domain Events a sus suscriptores."""
from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable

from farmaexpress.application.puertos import PublicadorDeEventos
from farmaexpress.domain.events import EventoDeDominio

log = logging.getLogger("farmaexpress.eventos")

Manejador = Callable[[EventoDeDominio], None]


class BusDeEventosEnMemoria(PublicadorDeEventos):
    def __init__(self) -> None:
        self._manejadores: dict[type, list[Manejador]] = defaultdict(list)
        self.publicados: list[EventoDeDominio] = []
        self.suscribir(EventoDeDominio, self._bitacora)

    def suscribir(self, tipo: type[EventoDeDominio], manejador: Manejador) -> None:
        self._manejadores[tipo].append(manejador)

    def publicar(self, eventos: list[EventoDeDominio]) -> None:
        for evento in eventos:
            self.publicados.append(evento)
            for tipo, manejadores in self._manejadores.items():
                if isinstance(evento, tipo):
                    for m in manejadores:
                        try:
                            m(evento)
                        except Exception:  # un suscriptor roto no revierte la venta
                            log.exception("Fallo el manejador de %s", evento.nombre)

    @staticmethod
    def _bitacora(evento: EventoDeDominio) -> None:
        log.info("%s pedido=%s %s", evento.nombre, evento.pedido_id, evento.payload())

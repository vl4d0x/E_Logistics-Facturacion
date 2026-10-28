"""Borra los datos de operación de prueba: servicios, viajes, facturas, pagos y todo lo que cuelga.

NO toca catálogos (clientes, lugares, mercancías, unidades, operadores), usuarios ni configuración.
Tampoco borra archivos de R2 ni nada en Facturama: solo la base de datos.

Sin argumentos solo cuenta lo que se borraría. Para borrar de verdad:
    cd backend && python -m scripts.limpiar_operacion --confirmar

Todo se borra en una sola transacción: o se borra todo o nada.
"""
import sys

from sqlalchemy import text
from sqlmodel import Session

from app.core.db import engine

# Orden de hijos a padres para respetar las llaves foráneas.
TABLAS = [
    "pago_aplicacion",
    "rep",
    "pago",
    "factura",
    "carga_combustible",
    "reporte_cierre",
    "inspeccion_salida",
    "acuse",
    "viaje_mercancia",
    "viaje",
    "servicio",
]


def main() -> None:
    confirmar = "--confirmar" in sys.argv[1:]

    with Session(engine) as session:
        conteos = {t: session.exec(text(f'SELECT count(*) FROM "{t}"')).one()[0] for t in TABLAS}
        for tabla, n in conteos.items():
            print(f"  {tabla:<20} {n}")

        if not confirmar:
            print("\nNo se borró nada. Vuelve a correrlo con --confirmar para borrar.")
            return

        for tabla in TABLAS:
            session.exec(text(f'DELETE FROM "{tabla}"'))
        session.commit()
        print(f"\n✅ Borrados {sum(conteos.values())} registros. Catálogos, usuarios y configuración intactos.")


if __name__ == "__main__":
    main()

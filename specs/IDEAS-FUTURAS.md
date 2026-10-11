# Ideas a futuro

Lista viva de mejoras acordadas con Vlad que **no** se construyen todavía.

## Kilómetros: corregir para mayor eficacia
- **Hoy (11 oct 2026)**: el km sugerido de un viaje sale del **km del destino para ese
  cliente** (columna KM del Excel de Carta Porte, cargado con *Catálogos → Lugares →
  Importar km*; `lugar.distancia_km` + `km_confirmado`). Si el destino no tiene km, se
  sugieren **70 km con la etiqueta "No confirmado"**. El origen no cuenta
  (`servicios.service.distancia_sugerida`).
- **Mejora**: km por par origen→destino real (la ubicación anterior del servicio es el
  origen de cada entrega) o con una tabla de distancias / API de rutas; al corregir un km a
  mano, guardarlo en el lugar como confirmado; mostrar el "No confirmado" también en el
  detalle del servicio (hoy solo se ve al capturar).

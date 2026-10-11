# Ideas a futuro

Lista viva de mejoras acordadas con Vlad que **no** se construyen todavía.

## Kilómetros: corregir para mayor eficacia
- **Hoy (11 oct 2026)**: el km sugerido de un viaje sale del **último km capturado hacia ese
  destino**, sin importar de dónde venga (`servicios.service.distancia_sugerida`). Es una
  aproximación: "de A a X" y "de B a X" comparten el mismo número aunque no sean la misma
  distancia. Se eligió así porque una entrega sola guarda su origen como `null` y el par
  origen→destino casi nunca existía (la sugerencia nunca se disparaba).
- **Mejora**: calcular el km por par origen→destino real (la ubicación anterior del
  servicio es el origen de cada entrega), o con una tabla de distancias entre lugares /
  una API de rutas; promediar varios viajes en vez de tomar el último; permitir que el
  admin corrija la distancia guardada de un lugar.

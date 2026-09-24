# 00 · Overview — Elogistics Facturación

> **Propósito de este documento**: dar a cualquier agente (o persona) el contexto mínimo para trabajar sobre el proyecto sin volver a preguntar. Léelo antes que cualquier otro spec. Las decisiones técnicas están en `01-architecture`; el modelo de datos en `02-data-model`; el contrato de API en `03-api-contract`; la lógica fiscal en `04-facturacion-cfdi`.

## 0. Convención — cuándo pedir información al usuario

A lo largo de estos specs hay bloques marcados así:

> 🔴 **INFO REQUERIDA (Vlad)** — descripción del dato que hace falta.

Marcan **datos del mundo real que solo Vlad puede dar**: credenciales y secretos, datos fiscales del emisor, los catálogos reales (unidades, operadores, clientes, mercancías), correos de facturación y valores por confirmar.

**Regla para cualquier agente:** cuando llegues a un bloque `INFO REQUERIDA`, **detente y pídele esos datos a Vlad antes de continuar esa parte.** No los inventes, no uses RFCs/claves/placeholders que parezcan reales, no adivines. Para avanzar en desarrollo puedes usar datos *claramente ficticios y rotulados como tales*, pero nada ficticio debe llegar a un timbrado real (ni siquiera en sandbox con datos de un tercero).

## 1. Qué es

Software web interno para **Elogistics**, una empresa de logística/autotransporte en el Estado de México (zona Toluca/Metepec). Automatiza la **facturación electrónica (CFDI 4.0) con Complemento Carta Porte 3.1** de sus servicios de transporte, un proceso que hoy se hace 100% a mano.

**Escala real (importante para dimensionar, NO sobre-ingenierizar):**
- ~8 unidades (camionetas)
- ~5 operadores
- ~6 clientes (empresas)
- Decenas de facturas al mes, no miles.

Es una herramienta interna de bajo volumen. **No** es un SaaS multi-tenant. Un solo emisor (una empresa). Prioridad: **rápido de construir y funcional**, no "robusto para escalar a millones".

## 2. El problema que resuelve

Hoy, cada factura se captura a mano en un portal externo, la Carta Porte (180+ campos) es lo más tardado, y hay que enviarla por correo al cliente junto con el acuse del servicio escaneado. Es tedioso, repetitivo y propenso a errores (que el SAT multa hasta ~$97,330 MXN por documento).

El sistema separa **la captura operativa** (rápida, en campo) del **acto fiscal** (facturar cuando hay tiempo), y precarga catálogos para que nadie teclee claves del SAT.

## 3. Concepto de dominio central

> **Un SERVICIO se compone de uno o más VIAJES.**

- Un **viaje** es un movimiento físico: una **recolección**, una **entrega**, o **recolección y entrega**.
- Un **servicio** agrupa uno o más viajes y es lo que se factura como **un solo CFDI**.
- Ejemplo: un día un operador va a cargar (recolección) y otros dos entregan en distintos puntos (entregas). Son 3 viajes → 1 servicio → 1 factura con 1 origen + N destinos en la Carta Porte.

El administrador registra viajes durante la operación y, cuando el servicio terminó, **agrupa** esos viajes en un servicio, le pone el subtotal y lo factura.

## 4. Roles

| Rol | Dónde trabaja | Qué hace |
|-----|---------------|----------|
| **Administrador** | Panel web de escritorio | Registra viajes, gestiona catálogos, agrupa viajes en servicios, factura (timbra), envía por correo, cancela, ve dashboard. |
| **Operador** | PWA en el celular (con **offline**) | Ve los viajes que tiene asignados, los cierra en campo: marca terminado, captura mercancía/kg, sube el acuse escaneado (o solo su referencia, o nada). |

## 5. Reglas de negocio que no son obvias (y muerden)

1. **Cierre del viaje por el operador** tiene 3 variantes según el cliente:
   - **Escaneo**: sube foto del acuse sellado.
   - **Referencia**: solo captura el folio/referencia del acuse (sin foto).
   - **Nada**: cuando solo fue a cargar (recolección), marca terminado sin adjunto.
   La variante la define una **configuración por cliente** (`cliente.modo_acuse`).
2. **El emisor es persona física** (régimen 612), no una razón social "Elogistics". Elogistics es marca comercial.
3. **Retención de 4% de IVA**: aplica cuando el servicio de autotransporte de carga se presta a una **persona moral**. Si el receptor es persona física, no aplica. Se calcula condicionalmente.
4. **Método de pago PPD** (pago en parcialidades o diferido): estos clientes pagan a crédito. Implica que más adelante habrá que emitir **Complemento de Pago (REP)** — modelado desde ahora, implementado en backlog.
5. **La descripción del concepto se autogenera** desde los datos ya capturados (unidad, origen, destino, fecha); no se teclea a mano.
6. **El operador nunca elige claves SAT.** Elige mercancía de una lista precargada por cliente; las claves (`ClaveProdServ`, `ClaveUnidad`, peso) van mapeadas por detrás.
7. **Modificar un servicio ya facturado** exige **cancelar la factura ante el SAT** primero (con motivo y acuse). No es un flag local.

## 6. Alcance del MVP (lo que SÍ se construye)

Auth (2 roles) · Catálogos (unidad, operador, cliente, mercancía frecuente) · Registro de viajes · Cierre de viajes por operador con offline · Agrupar viajes en servicios · Timbrado CFDI 4.0 + Carta Porte 3.1 vía Facturama · Validación pre-timbrado · Envío por correo con adjuntos · Cancelación · Dashboard de ingresos y pendientes · Export a Excel.

## 7. No-goals (lo que NO se construye ahora)

- No multi-empresa / multi-tenant.
- No app nativa (el operador usa PWA).
- No optimización de rutas, GPS tracking en vivo, ni nómina.
- No microservicios, colas de mensajes, ni event sourcing.
- **REP (complemento de pago)** y **plantillas de servicio recurrente**: quedan en backlog post-MVP (modelados, no implementados).

## 8. Fases de construcción (resumen)

Cada fase es una rebanada vertical (DB + API + UI) desplegable en Railway.

- **Fase 0 · Andamiaje**: repo, backend+DB+migraciones, frontend+shell PWA, auth, deploy a Railway. Spike de Facturama en sandbox (script que timbra un servicio inventado) para validar el mapeo temprano.
- **Fase 1 · Catálogos**: CRUD de unidad, operador, cliente, mercancía frecuente.
- **Fase 2 · Viajes**: admin registra; operador ve y cierra con sincronización offline.
- **Fase 3 · Servicios**: agrupar viajes, estados, subtotal.
- **Fase 4 · Facturación**: integración real Facturama, mapeo completo, validación pre-timbrado, PDF/XML.
- **Fase 5 · Entrega**: correo con adjuntos, cancelación, dashboard, export Excel.
- **Backlog**: REP, plantillas recurrentes.

## 9. Glosario

- **CFDI**: Comprobante Fiscal Digital por Internet (la factura electrónica). Versión 4.0.
- **Carta Porte**: complemento obligatorio del CFDI que ampara el traslado de mercancías. Versión 3.1.
- **CFDI de Ingreso (tipo I)**: el que emite el transportista que cobra el flete (nuestro caso).
- **PAC**: Proveedor Autorizado de Certificación; timbra el CFDI ante el SAT. Aquí usamos **Facturama**.
- **Timbrar**: sellar/certificar el CFDI ante el SAT (lo hace el PAC), obteniendo el UUID.
- **UUID / Folio Fiscal**: identificador único del CFDI timbrado.
- **PPD / PUE**: Pago en Parcialidades o Diferido / Pago en Una Exhibición.
- **REP**: Recibo Electrónico de Pago (complemento de pago), obligatorio en PPD al recibir el pago.
- **Acuse**: comprobante sellado por el cliente de que se entregó la mercancía.
- **Figura de transporte**: el operador (chofer), con su RFC y número de licencia (campo obligatorio del complemento).
- **Servicio / Viaje**: ver sección 3.

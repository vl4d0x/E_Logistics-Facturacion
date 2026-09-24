# Fase 1 · Catálogos

> **Objetivo**: CRUD de los catálogos que todo lo demás consume. Aquí vive el mapeo "apodo de unidad → datos de Carta Porte" y la config por cliente (modo de acuse, régimen).
> **Depende de**: Fase 0 (auth, esqueleto).
> **Entrega**: el admin puede administrar unidades, operadores, clientes y mercancías frecuentes desde el panel.
> **Lee antes**: `02-data-model §3.2-3.5`, `03-api-contract §5`.

## Historias de usuario

### H1.1 — Unidades
Como admin, quiero administrar mis unidades por apodo, para elegirlas rápido al registrar viajes.
**Criterios de aceptación**
- Puedo crear una unidad con: apodo, placa, año, config vehicular, peso bruto vehicular (**toneladas**), tipo y número de permiso SICT, aseguradora, póliza (`02-data-model §3.2`).
- El listado muestra el **apodo** como identificador visible; los datos SAT quedan en el detalle.
- Puedo editar y desactivar (soft-delete: `activo=false`, nunca borrado físico).
- El campo peso bruto vehicular advierte que es en toneladas (evita el error real de capturar kg).

### H1.2 — Operadores
Como admin, quiero administrar operadores con su RFC y licencia, porque son la figura de transporte obligatoria en la Carta Porte.
**Criterios de aceptación**
- Crear/editar/desactivar operador con nombre, RFC, número de licencia.
- RFC y licencia son obligatorios (validación de formato de RFC).

### H1.3 — Clientes
Como admin, quiero administrar clientes con su configuración fiscal y de acuse, para que la facturación y el cierre de viajes se comporten según cada cliente.
**Criterios de aceptación**
- Crear/editar/desactivar cliente con: razón social, RFC, CP fiscal, régimen fiscal, **régimen_receptor (física/moral)**, uso CFDI, método de pago default (PUE/PPD), **modo_acuse (escaneo/referencia/ninguno)**, email de facturación.
- `regimen_receptor` es obligatorio (decide la retención 4% después).
- `modo_acuse` es obligatorio (decide qué exige el cierre del operador).

### H1.4 — Mercancías frecuentes por cliente
Como admin, quiero precargar las mercancías típicas de cada cliente con sus claves SAT, para que el operador solo elija un nombre humano.
**Criterios de aceptación**
- Bajo un cliente, crear/editar/desactivar mercancías con: nombre humano, `BienesTransp` (clave SAT), `ClaveUnidad` (clave SAT), unidad descriptiva.
- El operador nunca verá las claves SAT, solo el nombre humano.

## Endpoints / pantallas
- Endpoints: `03-api-contract §5` (CRUD de unidades, operadores, clientes, mercancías).
- Pantallas admin: sección "Catálogos" con cuatro sub-vistas (tablas + formularios modales), siguiendo el diseño aprobado.

## INFO REQUERIDA (Vlad)
> 🔴 Los datos reales de todos los catálogos (ver bloque en `02-data-model §3`): unidades, operadores, clientes (con régimen físico/moral y modo de acuse), y mercancías frecuentes por cliente. Sin esto solo se prueban con datos ficticios rotulados.

## Casos borde
- No permitir desactivar una unidad/operador/cliente si tiene viajes activos sin facturar (o advertir).
- RFC inválido → `422` con mensaje claro.
- Editar una mercancía **no** debe alterar viajes/facturas pasadas (esas guardan snapshot; ver `02-data-model §3.7`).

## Definición de terminado
- [ ] CRUD completo de los 4 catálogos con soft-delete.
- [ ] Validaciones (RFC, obligatorios, régimen, modo de acuse).
- [ ] Solo admin accede.
- [ ] Tests: crear/editar/desactivar cada catálogo; validaciones; anidamiento mercancía↔cliente.

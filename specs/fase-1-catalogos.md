# Fase 1 · Catálogos y accesos

> **Objetivo**: que el admin administre **desde la UI, sin tocar código**, todo lo que el resto del sistema consume: unidades, operadores (y su acceso a la app), clientes, mercancías, lugares y otros administradores. Agregar, editar, "eliminar" (archivar cuando ya se usó) y restaurar.
> **Depende de**: Fase 0 (auth, esqueleto, deploy).
> **Entrega**: sección Catálogos completa + Configuración → Usuarios, desplegada en Railway.
> **Lee antes**: `02-data-model §3.1–3.6, §5`, `03-api-contract §5`, `05-ui-spec §5 (SmartDeleteDialog, FuelGauge), §7.5`.

## Historias de usuario

### H1.1 — Unidades
Como admin, quiero administrar mis camionetas por apodo, para elegirlas rápido y que la Carta Porte y la PWA se llenen solas.
**Criterios de aceptación**
- Crear/editar con los campos de `02 §3.2`, incluidos **tipo de medidor de gasolina** (aguja o barras + número de barras), capacidad del tanque y capacidad de carga.
- Al elegir "barras", el número de barras es obligatorio (2–20) y el formulario muestra una **vista previa del FuelGauge** tal como lo verá el operador.
- El campo peso bruto vehicular dice "en **toneladas**" y advierte si el valor parece kg (> 100).
- `apodo` y `placa` únicos (error claro si se repiten).
- El listado muestra el apodo como identificador; los datos SAT en el detalle.

### H1.2 — Operadores y su acceso a la app
Como admin, quiero dar de alta a un operador y darle acceso a la app, para que empiece a trabajar el mismo día sin ayuda técnica.
**Criterios de aceptación**
- Crear/editar operador con nombre, RFC (validación de formato), número de licencia y teléfono.
- Sección "Acceso a la app": **Dar acceso** (usuario/correo + contraseña temporal) crea un `usuario` con `rol=operador` ligado a la ficha; **Restablecer contraseña**; **Desactivar acceso** (el operador ya no puede iniciar sesión; sus servicios e historial se conservan).
- Un operador tiene a lo más un acceso; un usuario/correo no se repite.
- Para operadores el identificador de login no exige formato de correo (`01 §5`).
- Migración: si Fase 0 no creó la FK `usuario.operador_id → operador.id` y su `unique`, agregarlos aquí.

### H1.3 — Clientes
Como admin, quiero administrar clientes con su configuración fiscal y de acuse, para que la facturación y el cierre de viajes se comporten según cada uno.
**Criterios de aceptación**
- Crear/editar con `02 §3.4`: razón social, **nombre comercial** (el que se ve en la UI), RFC, CP fiscal, régimen fiscal, **física/moral**, uso CFDI, método de pago default (PPD), **modo de acuse** (escaneo/referencia/ninguno), **uno o varios correos** de facturación, días de crédito.
- `regimen_receptor` y `modo_acuse` obligatorios, con una línea de ayuda de qué provocan ("Moral: se retiene 4% de IVA", "Referencia: el operador solo captura el folio").
- Ficha del cliente con tabs: Datos fiscales · Mercancías · Lugares (la tab Tarifas llega en Fase 4).

### H1.4 — Mercancías frecuentes por cliente
Como admin, quiero precargar las mercancías típicas de cada cliente con sus claves SAT, para que el operador solo elija un nombre.
**Criterios de aceptación**
- En la tab Mercancías del cliente: crear/editar/eliminar con nombre humano, `BienesTransp`, `ClaveUnidad`, unidad descriptiva y **peso sugerido (kg)**.
- Editar una mercancía no altera viajes ni facturas existentes (snapshot).

### H1.5 — Lugares frecuentes
Como admin, quiero registrar los orígenes y destinos habituales, para crear servicios sin teclear direcciones y que la Carta Porte tenga el domicilio correcto.
**Criterios de aceptación**
- Crear/editar lugares con `02 §3.6`; ligados a un cliente o globales.
- Marcar uno como **origen predeterminado** por cliente (marcar otro desmarca el anterior).
- RFC del remitente/destinatario con default `XAXX010101000` y ayuda ("usa el RFC real si lo conoces").
- Vista global de lugares con filtro por cliente y buscador; también accesibles desde la tab Lugares del cliente.

### H1.6 — Eliminar, archivar y restaurar (todos los catálogos)
Como admin, quiero poder quitar lo que ya no uso sin romper facturas pasadas.
**Criterios de aceptación**
- "Eliminar" abre el **SmartDeleteDialog**, que consulta `GET …/{id}/uso`:
  - sin referencias → borrado definitivo;
  - con referencias → se **archiva** (`activo=false`) y se explica por qué;
  - con servicios `programado`/`en_curso` que lo usan → bloqueado, con la lista de servicios y enlaces para reasignar.
- Archivados: ocultos en selectores; visibles con el filtro "Archivados"; botón **Restaurar**.
- Aplica a unidades, operadores, clientes, mercancías y lugares.
- Implementa el conteo de referencias en un solo lugar por catálogo (`service.contar_uso`), para que las Fases 2–5 agreguen sus tablas (servicios, viajes, facturas, tarifas) sin tocar la UI. En Fase 1 solo existen referencias entre catálogos (cliente → mercancías/lugares, operador → usuario).

### H1.7 — Administradores
Como admin, quiero dar de alta a otra persona de la oficina como admin, sin pedírselo a un desarrollador.
**Criterios de aceptación**
- Configuración → Usuarios: listar, crear (nombre, correo, contraseña temporal), restablecer contraseña, desactivar.
- No puedo desactivarme a mí mismo ni dejar el sistema sin admins activos.

## Endpoints / pantallas
- Endpoints: `03 §5`.
- Pantallas: `05 §7.5` — Catálogos (Unidades, Operadores, Clientes con tabs, Lugares) y Configuración → Usuarios. Formularios en drawer.

## INFO REQUERIDA (Vlad)
> 🔴 Datos reales de catálogos (ver `02 §3`), incluyendo para cada unidad el **tipo de medidor** y **número de barras** (una foto del tablero sirve) y la **capacidad del tanque**; los **lugares** frecuentes; y con qué usuario/correo entrará cada operador.

## Casos borde
- RFC inválido → `422` junto al campo.
- Apodo/placa/correo duplicado → `422` con mensaje claro.
- Cambiar una unidad de "barras" a "aguja" no altera lecturas pasadas (se guardan con su tipo).
- Desactivar el acceso de un operador con un servicio en curso → advertir (su PWA dejará de sincronizar).
- Restaurar un cliente archivado restaura solo el cliente, no sus mercancías/lugares archivados (cada uno se restaura aparte).

## Definición de terminado
- [ ] CRUD + archivar/restaurar de unidades, operadores, clientes, mercancías y lugares, desde la UI.
- [ ] Acceso de operadores (dar, restablecer, desactivar) y administradores.
- [ ] Validaciones (RFC, únicos, régimen, modo de acuse, medidor).
- [ ] Solo admin accede; un operador con token recibe `403`.
- [ ] Tests: CRUD de cada catálogo; eliminar sin referencias vs archivar con referencias vs bloqueo con servicios activos; acceso de operador (login funciona tras crearlo y falla tras desactivarlo); reglas de último admin.

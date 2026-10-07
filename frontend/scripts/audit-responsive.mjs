/**
 * Auditoría de responsividad (`specs/05-ui-spec.md §3.1`).
 *
 * Recorre las pantallas del admin con Playwright a 390 px (teléfono), 820 px (tablet) y
 * 1280 px (laptop) y falla si alguna tiene scroll horizontal (de la página o del contenedor
 * principal) o deja visible la sidebar en < 992 px. Con SHOTS=1 guarda capturas para revisarlas
 * a ojo —la métrica no detecta lo feo, solo lo roto.
 *
 * Requisitos: backend y frontend corriendo (ej. API en :8765 con una base de PRUEBA, nunca la real,
 * y `VITE_API_URL=http://localhost:8765 npx vite --port 5199`) con un admin y algunos datos
 * (un servicio, una factura, un pago y un cliente) para que las pantallas de detalle existan.
 *
 * Uso (desde frontend/):
 *   API=http://localhost:8765/api/v1 APP=http://localhost:5199 ADMIN_USER=admin@test.mx \
 *   ADMIN_PASS=secret123 SHOTS=1 SHOTS_DIR=/tmp/capturas node scripts/audit-responsive.mjs
 * Opcionales: ONLY=cobranza (filtra rutas), SIZES='[["tel",390,844]]'.
 * Sale con código 1 si hay pantallas con desborde.
 */
import { chromium } from "playwright";
const API = process.env.API ?? "http://localhost:8765/api/v1";
const APP = process.env.APP ?? "http://localhost:5199";
const USER = process.env.ADMIN_USER ?? "admin@test.mx";
const PASS = process.env.ADMIN_PASS ?? "secret123";
const SC = process.env.SHOTS_DIR ?? ".";
const sizes = JSON.parse(process.env.SIZES || '[["tel",390,844],["tablet",820,1180],["laptop",1280,800]]');
const shots = process.env.SHOTS === "1";
const b = await chromium.launch();
const login = await (await fetch(API + "/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: USER, password: PASS }) })).json();
const H = { Authorization: "Bearer " + login.access_token };
const get = async (p) => (await fetch(API + p, { headers: H })).json();
const servicios = (await get("/servicios?size=5")).items ?? [];
const facturas = await get("/facturas");
const pagos = await get("/pagos");
const clientes = (await get("/catalogos/clientes")).items ?? [];
const sid = servicios[0]?.id, fid = facturas[0]?.id, pid = pagos[0]?.id, cid = clientes[0]?.id;
const rutas = [
  "/admin", "/admin/servicios?vista=programados", "/admin/servicios/nuevo", `/admin/servicios/${sid}`, `/admin/servicios/${sid}/facturar`,
  "/admin/facturas", `/admin/facturas/${fid}`, "/admin/cobranza", `/admin/cobranza?tab=por_cobrar&cliente=${cid}`, "/admin/cobranza?tab=pagos", "/admin/cobranza?tab=pagadas",
  `/admin/cobranza/pagos/${pid}`, "/admin/catalogos/unidades", "/admin/catalogos/operadores", "/admin/catalogos/clientes",
  `/admin/catalogos/clientes/${cid}`, "/admin/catalogos/lugares", "/admin/configuracion/usuarios", "/admin/configuracion/precios",
].filter((r) => !r.includes("undefined"));
const filtro = process.env.ONLY;
let problemas = 0;
for (const [nombre, w, h] of sizes) {
  const ctx = await b.newContext({ viewport: { width: w, height: h } });
  const p = await ctx.newPage();
  const errores = [];
  p.on("pageerror", (e) => errores.push(e.message));
  await p.goto(APP + "/login");
  await p.getByLabel("Usuario o correo").fill(USER);
  await p.getByLabel("Contraseña").fill(PASS);
  await p.getByRole("button", { name: /entrar|iniciar/i }).click();
  await p.waitForURL("**/admin**");
  for (const r of rutas) {
    if (filtro && !r.includes(filtro)) continue;
    await p.goto(APP + r);
    await p.waitForLoadState("networkidle");
    await p.waitForTimeout(400);
    const info = await p.evaluate(() => {
      const w = window.innerWidth;
      const doc = document.documentElement;
      const main = document.querySelector("main") || document.body;
      const limite = Math.min(w, main.getBoundingClientRect().right);
      const malos = [];
      for (const el of main.querySelectorAll("*")) {
        const rc = el.getBoundingClientRect();
        if (rc.width > 0 && rc.right > limite + 1) {
          let anc = el.parentElement, scroll = false;
          while (anc && anc !== main) { const o = getComputedStyle(anc).overflowX; if (o === "auto" || o === "scroll" || o === "hidden") { scroll = true; break; } anc = anc.parentElement; }
          if (!scroll) malos.push((el.className?.toString().split(" ")[0] || el.tagName) + ":" + Math.round(rc.right));
        }
      }
      const sidebar = document.querySelector("aside");
      const sidebarVisible = !!sidebar && getComputedStyle(sidebar).display !== "none";
      const desborde = doc.scrollWidth > w + 1 || main.scrollWidth > main.clientWidth + 1 || (w < 992 && sidebarVisible);
      return { desborde, scrollWidth: Math.max(doc.scrollWidth, main.scrollWidth), malos: [...new Set(malos)].slice(0, 4), sidebarVisible };
    });
    if (info.desborde) { problemas++; console.log(`✗ ${nombre} ${r} -> scrollWidth ${info.scrollWidth}/${w}; ${info.malos.join(", ")}`); }
    if (shots) await p.screenshot({ path: `${SC}/r_${nombre}_${r.replace(/[^a-z0-9]+/gi, "_")}.png`, fullPage: false });
  }
  if (errores.length) console.log(nombre, "pageerrors:", errores.slice(0, 3));
  await ctx.close();
}
console.log(problemas === 0 ? "SIN DESBORDES" : `${problemas} pantallas con desborde horizontal`);
await b.close();
process.exit(problemas === 0 ? 0 : 1);

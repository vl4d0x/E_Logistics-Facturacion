"""Búsqueda "inteligente" de los nombres del Excel de registros en los catálogos.

El Excel se captura a mano: los destinos vienen abreviados ("VASSA DIVASA" =
"DISTRIBUIDORA VASSA DIVASSA"), con la ciudad pegada ("TEPOTZOTLAN, QUALTIA") y varios
destinos en una celda ("DAS BESTE, JARVA"). Aquí no hay base de datos: funciones puras
que comparan textos y devuelven un puntaje 0-1.

- Las palabras comunes del catálogo ("ALIMENTOS", "DISTRIBUIDORA") pesan poco (IDF).
- Las palabras que solo coinciden con la ubicación del lugar (municipio/estado) o son
  vocabulario de ubicación ("CDMX", "EDO") no cuentan ni a favor ni en contra.
- Una celda con varios destinos se parte en la combinación que mejor encaja en el catálogo.
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

STOPWORDS = {
    "DE", "DEL", "LA", "LAS", "EL", "LOS", "Y", "E", "EN", "A", "AL",
    "SA", "CV", "S", "C", "V", "RL", "SAPI", "SAB", "SC", "SPR", "SRL", "AC", "SAS", "DECV",
}
# Palabras que describen dónde está el lugar, no quién es.
UBICACION = {
    "CDMX", "DF", "EDO", "EDOMEX", "MEX", "MEXICO", "ESTADO", "CD", "CIUDAD", "MPIO", "COL",
    "NORTE", "SUR", "ORIENTE", "PONIENTE", "PLANTA", "CEDIS", "BODEGA", "ALMACEN",
    # Municipios y ciudades que aparecen pegados al destino en el Excel ("TEPOTZOTLAN, QUALTIA").
    "TOLUCA", "LERMA", "METEPEC", "ZINACANTEPEC", "TEPOTZOTLAN", "IXTLAHUACA", "TLALNEPANTLA",
    "TLANEPANTLA", "NAUCALPAN", "ECATEPEC", "TULTITLAN", "CUAUTITLAN", "CUAUTITLAN IZCALLI",
    "IZCALLI", "TEOLOYUCAN", "ZUMPANGO", "TECAMAC", "TEXCOCO", "NEZAHUALCOYOTL", "CHALCO",
    "IXTAPALUCA", "HUIXQUILUCAN", "ATIZAPAN", "COACALCO", "NICOLAS", "ROMERO", "OCOYOACAC",
    "TIANGUISTENCO", "TEANGUISTENCO", "XONACATLAN", "ATLACOMULCO", "JILOTEPEC", "VALLEJO",
    "AZCAPOTZALCO", "IZTAPALAPA", "IZTACALCO", "COYOACAN", "TLALPAN", "XOCHIMILCO", "GAM",
    "CUAUHTEMOC", "MIGUEL", "HIDALGO", "BENITO", "JUAREZ", "VENUSTIANO", "CARRANZA", "TLAHUAC",
    "QUERETARO", "QRO", "PUEBLA", "TLAXCALA", "PACHUCA", "TIZAYUCA", "CUERNAVACA", "CIVAC",
    "CELAYA", "IRAPUATO", "SALAMANCA", "LEON", "GUADALAJARA", "MONTERREY", "SLP", "MORELIA",
    "AIFA", "AEROPUERTO", "VERACRUZ", "ORIZABA",
}
# Palabras de la operación, no del lugar ("MUESTRAS THALIA", "POLVILLAS CON MANIOBRA").
RUIDO = {
    "MUESTRA", "MUESTRAS", "CON", "SIN", "MANIOBRA", "MANIOBRAS", "RECOLECTAR", "RECOGER",
    "RECOLECCION", "ENTREGA", "ENTREGAR", "TIRO", "FALSO", "REGRESO", "RETORNO", "DOCUMENTOS",
    "PARA", "LIC", "SR", "SRA", "ING", "CAJAS", "CAJA", "TAMBO", "TAMBOS",
}
_CIUDADES_COMPUESTAS = [c for c in UBICACION if " " in c]

UMBRAL_ALTA = 0.8
UMBRAL_MEDIA = 0.55


def normalizar(texto: object) -> str:
    """Mayúsculas, sin acentos ni BOM, solo letras/números separados por un espacio."""
    if texto is None:
        return ""
    s = str(texto).replace("﻿", "")
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^A-Za-z0-9Ññ]+", " ", s).upper()
    return " ".join(s.split())


def _sin_parentesis(texto: object) -> str:
    return re.sub(r"\([^)]*\)?", " ", str(texto or ""))


def tokens(texto: object) -> list[str]:
    return [t for t in normalizar(_sin_parentesis(texto)).split() if t not in STOPWORDS]


def es_ubicacion(texto: str) -> bool:
    """El pedazo solo dice dónde o qué se hizo ("TEPOTZOTLAN", "ENTREGA"), no a quién."""
    ts = tokens(texto)
    return bool(ts) and all(t in UBICACION or t in RUIDO or t.isdigit() for t in ts)


def tokens_coinciden(a: str, b: str) -> bool:
    if a == b:
        return True
    if min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)):
        return True
    return min(len(a), len(b)) >= 5 and SequenceMatcher(None, a, b).ratio() >= 0.84


@dataclass
class Candidato:
    id: object
    nombre: str
    # Otros nombres por los que se le conoce (razón social, destinatario…).
    alias: list[str] = field(default_factory=list)
    # Municipio, localidad, estado: palabras que no lo identifican, solo lo ubican.
    ubicacion: list[str] = field(default_factory=list)
    preferido: bool = False  # desempate (p. ej. el origen predeterminado del cliente)
    _tokens: list[str] = field(default_factory=list, repr=False)
    _ubic: set[str] = field(default_factory=set, repr=False)
    _junto: str = field(default="", repr=False)

    def preparar(self) -> None:
        vistos: list[str] = []
        for texto in [self.nombre, *self.alias]:
            for t in tokens(texto):
                if t not in vistos:
                    vistos.append(t)
        self._tokens = vistos
        self._ubic = {t for u in self.ubicacion for t in tokens(u)}
        self._junto = "".join(normalizar(x).replace(" ", "") for x in [self.nombre, *self.alias])


class Indice:
    """Catálogo preparado para buscar: calcula el peso (IDF) de cada palabra una sola vez."""

    def __init__(self, candidatos: list[Candidato]):
        self.candidatos = candidatos
        df: dict[str, int] = {}
        for c in candidatos:
            c.preparar()
            for t in set(c._tokens):
                df[t] = df.get(t, 0) + 1
        self._df = df
        self._n = max(len(candidatos), 1)

    def peso(self, token: str) -> float:
        return math.log(1 + self._n / (1 + self._df.get(token, 0))) + 0.25

    def puntaje(self, consulta: str, c: Candidato) -> float:
        q = tokens(consulta)
        if not q:
            return 0.0
        q_junto = normalizar(consulta).replace(" ", "")
        if q_junto and q_junto == c._junto:
            return 1.0
        # "THYSSEN KRUPP" = "THYSSENKRUPP": dos palabras seguidas que juntas son una del lugar.
        unidas: list[str] = []
        i = 0
        while i < len(q):
            junta = q[i] + q[i + 1] if i + 1 < len(q) else ""
            if junta and any(
                ct == junta or (len(ct) >= 8 and SequenceMatcher(None, junta, ct).ratio() >= 0.9) for ct in c._tokens
            ):
                unidas.append(q[i] + q[i + 1])
                i += 2
            else:
                unidas.append(q[i])
                i += 1
        q = unidas
        total = encontrado = 0.0
        usados: set[str] = set()
        distintivo = False
        for t in q:
            match = next((ct for ct in c._tokens if tokens_coinciden(t, ct)), None)
            if match is None and len(t) >= 6 and t in c._junto:
                match = t  # "MAVACARR" dentro de "...MAVACARR"
            if match is not None:
                w = self.peso(t)
                total += w
                encontrado += w
                usados.add(match)
                distintivo = distintivo or self._df.get(match, 0) <= 2 or len(match) >= 9
                continue
            if t in UBICACION or t in RUIDO or t.isdigit() or any(tokens_coinciden(t, u) for u in c._ubic):
                continue  # neutra: ubica, no identifica
            total += self.peso(t)
        if total == 0:
            return 0.3 if q else 0.0  # solo palabras de ubicación
        cobertura_q = encontrado / total
        total_c = sum(self.peso(t) for t in c._tokens) or 1.0
        cobertura_c = sum(self.peso(t) for t in usados) / total_c
        score = 0.8 * cobertura_q + 0.2 * cobertura_c
        # Todas las palabras del lugar aparecen en el texto (el texto trae de más, p. ej. un
        # contacto): cuenta si lo que coincidió no es una sola palabra común.
        if cobertura_c >= 0.999 and encontrado >= 0.4 * total and encontrado >= 1.5:
            score = max(score, 0.85)
        if not distintivo:
            score = min(score, 0.6)  # solo coincidió una palabra que traen muchos lugares
        return min(score, 1.0)

    def buscar(self, consulta: str, limite: int = 5) -> list[tuple[Candidato, float]]:
        res = [(c, self.puntaje(consulta, c)) for c in self.candidatos]
        res = [r for r in res if r[1] > 0]
        res.sort(key=lambda r: (r[1], r[0].preferido), reverse=True)
        return res[:limite]


def confianza(score: float) -> str:
    if score >= UMBRAL_ALTA:
        return "alta"
    if score >= UMBRAL_MEDIA:
        return "media"
    return "ninguna"


_SEPARADORES = re.compile(r"\s*[,;/]\s*|\s+-\s*|\s*-\s+|\s+\+\s+|\s+\.\s+")


def segmentos(texto: str) -> list[str]:
    """Pedazos de la celda; una ciudad suelta se pega al pedazo de al lado."""
    crudos = [s.strip() for s in _SEPARADORES.split(str(texto or "")) if s and s.strip(" .")]
    res: list[str] = []
    pendiente: str | None = None
    for s in crudos:
        if es_ubicacion(s) and len(crudos) > 1:
            if res and pendiente is None and not es_ubicacion(res[-1]):
                res[-1] = f"{res[-1]}, {s}"
            else:
                pendiente = f"{pendiente}, {s}" if pendiente else s
            continue
        if pendiente:
            s = f"{pendiente}, {s}"
            pendiente = None
        res.append(s)
    if pendiente:
        if res:
            res[-1] = f"{res[-1]}, {pendiente}"
        else:
            res.append(pendiente)
    return res


@dataclass
class Grupo:
    texto: str
    resultados: list[tuple[Candidato, float]]

    @property
    def mejor(self) -> tuple[Candidato, float] | None:
        return self.resultados[0] if self.resultados else None


def partir_destinos(texto: str, indice: Indice, max_union: int = 4) -> list[Grupo]:
    """Parte la celda en destinos: elige la combinación de segmentos consecutivos que
    mejor encaja (cada destino reconocido suma; uno desconocido resta un poco, así una
    ciudad suelta se queda pegada a su destino en vez de volverse otro)."""
    segs = segmentos(texto)
    if not segs:
        return []
    n = len(segs)
    cache: dict[tuple[int, int], Grupo] = {}

    def grupo(i: int, j: int) -> Grupo:
        if (i, j) not in cache:
            t = ", ".join(segs[i:j])
            cache[(i, j)] = Grupo(t, indice.buscar(t))
        return cache[(i, j)]

    def valor(g: Grupo, partes: int) -> float:
        s = g.mejor[1] if g.mejor else 0.0
        if s >= UMBRAL_ALTA:
            return s - 0.5
        # Desconocido: cada pedazo es su propio destino, salvo que juntos sí encajen.
        return 0.02 - 0.3 * (partes - 1)  # en empate, mejor separar

    mejor: list[tuple[float, list[Grupo]]] = [(0.0, [])] + [(-math.inf, [])] * n
    for j in range(1, n + 1):
        for i in range(max(0, j - max_union), j):
            base, grupos = mejor[i]
            if base == -math.inf:
                continue
            g = grupo(i, j)
            v = base + valor(g, j - i)
            # Dos pedazos seguidos que caen en el mismo lugar son el mismo destino.
            if grupos and g.mejor and grupos[-1].mejor and g.mejor[0].id == grupos[-1].mejor[0].id:
                v -= 0.6
            if v > mejor[j][0] + 1e-9:
                mejor[j] = (v, [*grupos, g])
    return mejor[n][1]


_KG = re.compile(r"(\d+(?:[.,]\d+)?)\s*KG", re.IGNORECASE)


def kg_en_texto(texto: object) -> float | None:
    m = _KG.search(str(texto or ""))
    return float(m.group(1).replace(",", ".")) if m else None


def varios(texto: object) -> list[str]:
    """"ISRAEL, ALDO" → ["ISRAEL", "ALDO"] (operadores o unidades capturados juntos)."""
    return [s for s in re.split(r"\s*[,/&+]\s*|\s+Y\s+", str(texto or "").strip()) if s.strip()]


# Nombres del Excel que no se parecen a la unidad del catálogo: apodo del Excel → placa.
# (Vlad, 3 nov 2026: la "KICKS" del registro es la SAVEIRO BLANCA.)
UNIDAD_ALIAS_FIJOS = {
    "KICKS": "KR9417A",
    "KICKS GRIS": "KR9417A",
}

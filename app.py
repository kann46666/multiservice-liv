# app.py – V8.6 + notify.mp3 (Actualizado: Tarjeta Amarilla para SKUs Repetidos/Omitidos)
# - NUEVO V8.6: Detección visual de duplicados con Tarjeta Amarilla de advertencia.
# - V8.5: Ajustes de procesamiento agrupados en un Accordion. Botones reubicados.
# - V8.4: Tarjetas Roja y Verde estáticas y forzadas a Dark Mode.
# - V8.3: Círculo de carga inline.
# - V8.2: Input numérico para limitar cantidad de destacados.
# - V8.1: Live-streaming. La galería se actualiza producto por producto.

import os
import re
import time
import random
import json
import zipfile
import typing as t
import concurrent.futures
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import unquote, urljoin

import pandas as pd
import gradio as gr
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter, Retry

# ---- Google Search opcional
try:
    from googlesearch import search
    HAS_GOOGLESEARCH = True
except Exception:
    HAS_GOOGLESEARCH = False

# ============================ Catálogo ============================

CATALOGO_LIVERPOOL = {
    "Mujer": {
        "Ropa": {
            "Blusas": "https://www.liverpool.com.mx/tienda/blusas/catst4003088",
            "Playeras": "https://www.liverpool.com.mx/tienda/playeras/catst25229539",
            "Jeans": "https://www.liverpool.com.mx/tienda/jeans/catst4003090",
            "Ropa Interior y Pijamas": "https://www.liverpool.com.mx/tienda/ropa-interior-y-pijamas/catst4003107",
            "Pantalones Para Mujer": "https://www.liverpool.com.mx/tienda/pantalones-para-mujer/catst44218417",
            "Sets de vestir": "https://www.liverpool.com.mx/tienda/sets-de-vestir/catst86068808",
            "Trajes de Baño": "https://www.liverpool.com.mx/tienda/trajes-de-ba%C3%B1o/catst4003171",
            "Vestidos": "https://www.liverpool.com.mx/tienda/vestidos/catst4003101",
            "Faldas": "https://www.liverpool.com.mx/tienda/faldas/catst44217998",
            "Shorts y Bermudas": "https://www.liverpool.com.mx/tienda/shorts-y-bermudas/catst44218006",
            "Suéteres": "https://www.liverpool.com.mx/tienda/su%C3%A9teres/catst4011919",
            "Sudaderas": "https://www.liverpool.com.mx/tienda/sudaderas/catst51446716",
            "Chamarras": "https://www.liverpool.com.mx/tienda/chamarras/catst16991493",
            "Abrigos y gabardinas": "https://www.liverpool.com.mx/tienda/abrigos-y-gabardinas/catst9643704",
            "Sacos y Blazers": "https://www.liverpool.com.mx/tienda/sacos-y-blazers/catst51446696",
            "Capas y Kimonos": "https://www.liverpool.com.mx/tienda/capas-y-kimonos/catst7418935",
            "Chalecos": "https://www.liverpool.com.mx/tienda/chalecos/catst44217972",
            "Body Casual": "https://www.liverpool.com.mx/tienda/body-casual/catst54234581",
            "Urban Zone": "https://www.liverpool.com.mx/tienda/urban-zone/catst54234561",
            "Confort": "https://www.liverpool.com.mx/tienda/confort/catst44218445",
            "Leggings": "https://www.liverpool.com.mx/tienda/leggings/catst44218027",
            "Jumpsuits": "https://www.liverpool.com.mx/tienda/jumpsuits/catst44217990",
            "Ropa de Maternidad": "https://www.liverpool.com.mx/tienda/ropa-de-maternidad/catst4003215",
            "Tallas Extra de Mujer": "https://www.liverpool.com.mx/tienda/tallas-extra-de-mujer/catst4003199"
        },
        "Zapatos": {
            "Tenis Casuales": "https://www.liverpool.com.mx/tienda/tenis-casuales/catst4003357",
            "Bota": "https://www.liverpool.com.mx/tienda/bota/catst85235913",
            "Botín": "https://www.liverpool.com.mx/tienda/bota/catst85235913",
            "Flats": "https://www.liverpool.com.mx/tienda/flats/catst4003355",
            "Tacones": "https://www.liverpool.com.mx/tienda/zapatillas/catst4003352",
            "Tenis deportivos": "https://www.liverpool.com.mx/tienda/tenis-deportivos/catst54234603",
            "Mocasines": "https://www.liverpool.com.mx/tienda/mocasines/catst85235919",
            "Mules & Sliders": "https://www.liverpool.com.mx/tienda/mules-&-sliders/catst85236057",
            "Alpargatas": "https://www.liverpool.com.mx/tienda/alpargatas/catst44165033",
            "Sandalias": "https://www.liverpool.com.mx/tienda/sandalias/catst4003354",
            "Confort": "https://www.liverpool.com.mx/tienda/confort/catst4003356",
            "Pantuflas": "https://www.liverpool.com.mx/tienda/pantuflas/catst25230066",
            "Accesorios de Calzado y Limpieza": "https://www.liverpool.com.mx/tienda/accesorios-de-calzado-y-limpieza/catst44165071"
        },
        "Bolsas": {
            "Tote": "https://www.liverpool.com.mx/tienda/tote/catst4003492",
            "Crossbody y Cangureras": "https://www.liverpool.com.mx/tienda/crossbody-y-cangureras/catst4003546",
            "Satchel": "https://www.liverpool.com.mx/tienda/satchel/catst4003548",
            "Backpacks": "https://www.liverpool.com.mx/tienda/backpacks/catst4003549",
            "Carteras": "https://www.liverpool.com.mx/tienda/carteras/catst4003480",
            "Bowler": "https://www.liverpool.com.mx/tienda/bowler/catst4003547",
            "Clutch": "https://www.liverpool.com.mx/tienda/clutch/catst4003550",
            "Bolsa de mano": "https://www.liverpool.com.mx/tienda/bolsa-de-mano/catst44162579",
            "Bolsa Bucket": "https://www.liverpool.com.mx/tienda/bolsa-bucket/catst44162595",
            "Pañalera": "https://www.liverpool.com.mx/tienda/pa%C3%B1alera/catst85604726"
        },
        "Lentes": {
            "Armazones": "https://www.liverpool.com.mx/tienda/armazones/catst4006850",
            "Lentes Solares": "https://www.liverpool.com.mx/tienda/lentes-solares/catst4006849",
            "Lentes para computadora": "https://www.liverpool.com.mx/tienda/lentes-para-computadora/catst44164268",
            "Lentes de contacto": "https://www.liverpool.com.mx/tienda/lentes-de-contacto/catst19676491"
        },
        "Relojeria": {
            "Relojes": "https://www.liverpool.com.mx/tienda/relojes/catst44216705",
            "Alta Joyería": "https://www.liverpool.com.mx/tienda/alta-joyer%C3%ADa/catst84073477",
            "Collares y Cadenas": "https://www.liverpool.com.mx/tienda/collares-y-cadenas/catst44216748",
            "Aretes": "https://www.liverpool.com.mx/tienda/aretes/catst44216730",
            "Pulseras": "https://www.liverpool.com.mx/tienda/pulseras/catst44216764",
            "Anillos": "https://www.liverpool.com.mx/tienda/anillos/catst44216750",
            "Anillos de Compromiso": "https://www.liverpool.com.mx/tienda/anillos-de-compromiso/catst44216715",
            "Sets de aretes, pulseras y anillos": "https://www.liverpool.com.mx/tienda/sets-de-aretes,-pulseras-y-anillos/catst44216793",
            "Correas y Accesorios": "https://www.liverpool.com.mx/tienda/correas-y-accesorios/catst76402556"
        },
        "Ropa Deportiva": {
            "Mallas y leggings": "https://www.liverpool.com.mx/tienda/mallas-y-leggings/catst83621313",
            "Playeras": "https://www.liverpool.com.mx/tienda/mallas-y-leggings/catst83621313", 
            "Tops y bras deportivos": "https://www.liverpool.com.mx/tienda/playeras/catst83621365",
            "Shorts y faldas": "https://www.liverpool.com.mx/tienda/tops-y-bras-deportivos/catst83621382",
            "Conjuntos deportivos": "https://www.liverpool.com.mx/tienda/shorts-y-faldas/catst83621383",
            "Sudaderas": "https://www.liverpool.com.mx/tienda/conjuntos-deportivos/catst83621387",
            "Chamarras y chalecos": "https://www.liverpool.com.mx/tienda/sudaderas/catst83621423",
            "Pants": "https://www.liverpool.com.mx/tienda/chamarras-y-chalecos/catst83621434",
            "Trajes de Baño": "https://www.liverpool.com.mx/tienda/pants/catst85094167",
            "Jerseys": "https://www.liverpool.com.mx/tienda/trajes-de-ba%C3%B1o/catst85094169"
        },
        "Accesorios Mujer": {
            "Cinturones": "https://www.liverpool.com.mx/tienda/cinturones/catst6477228",
            "Pashminas y Mascadas": "https://www.liverpool.com.mx/tienda/pashminas-y-mascadas/catst6477237",
            "Sombreros y Gorras": "https://www.liverpool.com.mx/tienda/sombreros-y-gorras/catst6477240",
            "Accesorios para el cabello": "https://www.liverpool.com.mx/tienda/accesorios-para-el-cabello/catst83551944",
            "Paraguas": "https://www.liverpool.com.mx/tienda/paraguas/catst9207491"
        },
        "Perfumes": {
            "Todo Perfumes": "https://www.liverpool.com.mx/tienda/perfumes/catst54488393"
        },
        "Novedades Mujer": {
            "Todo Novedades": "https://www.liverpool.com.mx/tienda/novedades-para-mujer/catst83975888"
        },
        "Basicos": {
            "Todo Básicos": "https://www.liverpool.com.mx/tienda/b%C3%A1sicos/catst83850477"
        },
        "Marcas diseñador": {
            "Todo Diseñador": "https://www.liverpool.com.mx/tienda/marcas-de-dise%C3%B1ador/catst83801734"
        }
    }
}

# ============================ Config ============================

PATRON_IMG = r"https://(?:ss|sp)\d+\.liverpool\.com\.mx/(?:xl|i)/[\w\d\-\_]+\.jpg"
BASE_IMG_FALLBACK = "https://sp540.liverpool.com.mx/i/"
BASE_PDP = "https://www.liverpool.com.mx/tienda/pdp"
BASE_HOME = "https://www.liverpool.com.mx"
DEFAULT_TIMEOUT = 5
NOTIFY_SOUND = os.environ.get("CUSTOM_NOTIFY_SOUND", "notify.mp3")

def slug_a_nombre(slug: str) -> str:
    if not slug: return ""
    s = unquote(slug).split("?")[0].split("#")[0]
    s = s.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", s).strip().title()

def _coerce_nonempty_str(x: t.Any) -> str: return ("" if pd.isna(x) else str(x)).strip()

def normalize_sku(raw: t.Any) -> str:
    s = _coerce_nonempty_str(raw)
    if s.endswith(".0"): s = s[:-2]
    return re.sub(r"\D+", "", s)

def fmt_duration(seconds: float) -> str:
    if seconds is None or seconds != seconds or seconds < 0: return "—"
    s = int(round(seconds))
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h > 0: return f"{h}h {m}m {s}s"
    if m > 0: return f"{m}m {s}s"
    return f"{s}s"

# V8.6 FIX: Modificación para detectar, rastrear y retornar duplicados.
def parse_grouped_skus(text: str) -> tuple[list[tuple[str, str]], dict[str, list[str]]]:
    out = []
    seen = set()
    duplicates = {}
    current_category = "General"
    
    for line in text.splitlines():
        parts = re.split(r'(\b\d{5,}(?:\.0)?\b)', line)
        for p in parts:
            if not p: continue
            if re.fullmatch(r'\b\d{5,}(?:\.0)?\b', p):
                sku = normalize_sku(p)
                if sku:
                    if sku not in seen:
                        seen.add(sku)
                        out.append((current_category, sku))
                    else:
                        # Si ya lo vimos, lo guardamos en los duplicados
                        if current_category not in duplicates:
                            duplicates[current_category] = []
                        duplicates[current_category].append(sku)
            else:
                clean_text = p.strip(' \t\n\r,-:|')
                if clean_text and re.search(r'[^\W\d_]', clean_text):
                    current_category = re.sub(r'\s+', ' ', clean_text)
    return out, duplicates

# ============================ Cliente ============================

@dataclass(frozen=True)
class ClientConfig:
    timeout: int = DEFAULT_TIMEOUT
    base_pdp: str = BASE_PDP
    base_img_fallback: str = BASE_IMG_FALLBACK
    patron_img: str = PATRON_IMG
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, como Gecko) Chrome/124.0 Safari/537.36"

class LiverpoolClient:
    def __init__(self, cfg: ClientConfig | None = None):
        self.cfg = cfg or ClientConfig()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.cfg.user_agent,
            "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Connection": "close",
            "Referer": BASE_HOME,
        })
        retries = Retry(total=1, backoff_factor=0.3, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=frozenset(["GET", "HEAD"]), raise_on_status=False)
        adapter = HTTPAdapter(max_retries=retries, pool_maxsize=15)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self._img_cache = {}

    def _get_html(self, url: str) -> str:
        try:
            r = self.session.get(url, timeout=self.cfg.timeout)
            if r.status_code == 200 and r.text: return r.text
        except: pass
        return ""

    def extraer_skus_de_categoria(self, url: str, limit: int = 50) -> list[str]:
        html = self._get_html(url)
        if not html: return []
        skus = []
        soup = BeautifulSoup(html, "html.parser")
        
        script_next = soup.find("script", id="__NEXT_DATA__")
        if script_next:
            try:
                data = json.loads(script_next.string)
                records = data.get("props", {}).get("pageProps", {}).get("initialState", {}).get("plp", {}).get("plpState", {}).get("records", [])
                for rec in records:
                    sku = rec.get("productId")
                    if sku and sku not in skus:
                        skus.append(sku)
                if skus:
                    return skus[:limit]
            except: pass
            
        main_content = soup.find("main") or soup
        for a in main_content.find_all("a", href=True):
            href = a["href"]
            if "/tienda/pdp/" in href:
                m = re.search(r"/tienda/pdp/[^/]+/(\d{5,})", href)
                if m:
                    sku = m.group(1)
                    if sku not in skus: skus.append(sku)
        
        return skus[:limit]

    def _check_single_url(self, url: str) -> bool:
        try:
            r = self.session.head(url, timeout=3, allow_redirects=True)
            if r.status_code == 200 and "image" in r.headers.get("Content-Type", "").lower(): return True
            rg = self.session.get(url, timeout=3, stream=True)
            chunk = next(rg.iter_content(chunk_size=64), b"")
            return rg.status_code == 200 and bool(chunk)
        except: return False

    def _check_image_validity(self, url: str) -> bool:
        if not url: return False
        if url in self._img_cache: return self._img_cache[url]
        is_valid = self._check_single_url(url)
        self._img_cache[url] = is_valid
        return is_valid

    def _check_validity_bulk(self, urls: list[str]) -> dict[str, bool]:
        results = {}
        to_check = []
        for u in urls:
            if u in self._img_cache: results[u] = self._img_cache[u]
            else: to_check.append(u)
        if to_check:
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                future_to_url = {executor.submit(self._check_single_url, u): u for u in to_check}
                for future in concurrent.futures.as_completed(future_to_url):
                    u = future_to_url[future]
                    try: is_valid = future.result()
                    except: is_valid = False
                    results[u] = is_valid
                    self._img_cache[u] = is_valid
        return results

    @lru_cache(maxsize=4096)
    def buscar_slug_en_liverpool(self, sku: str) -> str:
        if not sku: return ""
        html = self._get_html(f"{BASE_HOME}/tienda?s={sku}")
        if not html: return ""
        if 'data-testid="null-search-landing"' in html or 'search-not-found-content' in html: return ""
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            if "/pdp/" in a["href"]:
                m = re.search(r"/pdp/([^/]+)/?", a["href"])
                if m: return m.group(1).strip()
        m = re.search(r"/pdp/([^/]+)/", html)
        return m.group(1).strip() if m else ""

    @lru_cache(maxsize=4096)
    def buscar_slug_por_google(self, sku: str) -> str:
        if not (HAS_GOOGLESEARCH and sku): return ""
        try:
            for url in search(f"{sku} site:liverpool.com.mx", num_results=5):
                if ("liverpool.com.mx" in url) and ("/pdp/" in url):
                    parts = url.split("/pdp/")
                    if len(parts) > 1: return parts[1].split("/")[0].strip()
        except: pass
        return ""

    @lru_cache(maxsize=4096)
    def candidatos_pdp_desde_busqueda(self, sku: str) -> list[str]:
        out = []
        html = self._get_html(f"{BASE_HOME}/tienda?s={sku}")
        if not html or 'data-testid="null-search-landing"' in html or 'search-not-found-content' in html: return out
        soup = BeautifulSoup(html, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True):
            if "/pdp/" in a["href"]:
                abs_url = urljoin(BASE_HOME, a["href"])
                if abs_url not in seen:
                    seen.add(abs_url)
                    out.append(abs_url)
        return out

    def _get_prefix(self, url: str) -> str:
        m = re.match(r"^(\d+)", url.split('/')[-1])
        if m: return f"{url.rsplit('/', 1)[0]}/{m.group(1)}"
        return re.sub(r"(_|-)[0-9]+[a-zA-Z]?$", "", url.replace(".jpg.jpg", ".jpg").replace(".jpg", ""))

    def _deducir_base_y_variantes(self, main_img: str, thumb_imgs: list[str], html: str) -> list[str]:
        candidatos = []
        if main_img: candidatos.append(main_img)
        candidatos.extend(thumb_imgs)
        cands_uniq = []
        for c in candidatos:
            if c and c not in cands_uniq: cands_uniq.append(c)
        if main_img and len(cands_uniq) < 6:
            main_prefix = self._get_prefix(main_img)
            extra_cands = set(u for u in re.findall(self.cfg.patron_img, html, flags=re.IGNORECASE) if u.startswith(main_prefix) and u.endswith(".jpg"))
            extra_cands.add(f"{main_prefix}.jpg")
            for i in range(1, 7):
                extra_cands.update([f"{main_prefix}_{i}p.jpg", f"{main_prefix}-{i}p.jpg", f"{main_prefix}_{i}.jpg", f"{main_prefix}-{i}.jpg"])
            for url in sorted(list(extra_cands)):
                if url not in cands_uniq: cands_uniq.append(url)
        validities = self._check_validity_bulk(cands_uniq)
        finales = [u for u in cands_uniq if validities.get(u, False)]
        return (finales + [""]*6)[:6]

    @lru_cache(maxsize=4096)
    def extraer_imagenes_de_html(self, html: str, sku: str = "") -> list[str]:
        if not html: return [""]*6
        soup = BeautifulSoup(html, "html.parser")
        main_img = ""
        thumb_imgs = []
        tag_main = soup.find("img", {"data-testid": re.compile(r"gallery.*main.*image", re.I)})
        if tag_main:
            src = tag_main.get("src") or tag_main.get("data-src", "")
            if re.search(self.cfg.patron_img, src, flags=re.IGNORECASE): main_img = src
        for tag in soup.find_all("img", {"data-testid": re.compile(r"gallery.*thumbnail.*image", re.I)}):
            src = tag.get("src") or tag.get("data-src", "")
            if src and re.search(self.cfg.patron_img, src, flags=re.IGNORECASE): thumb_imgs.append(src)
        if not main_img:
            meta_og = soup.find("meta", property="og:image")
            if meta_og and meta_og.get("content") and re.search(self.cfg.patron_img, meta_og.get("content").strip(), flags=re.IGNORECASE):
                main_img = meta_og.get("content").strip()
        if not main_img and sku:
            for u in re.findall(self.cfg.patron_img, html, flags=re.IGNORECASE):
                if sku in u: main_img = u; break
        if not main_img:
            m = re.search(self.cfg.patron_img, html, flags=re.IGNORECASE)
            if m: main_img = m.group(0)
        return self._deducir_base_y_variantes(main_img, thumb_imgs, html)

    @lru_cache(maxsize=4096)
    def extraer_datos_pdp(self, pdp_url: str) -> tuple[float, float, str, str, str, str]:
        if not pdp_url: return 0.0, 0.0, "", "", "", "Disponible"
        html = self._get_html(pdp_url)
        if not html: return 0.0, 0.0, "", "", "", "Disponible"
        soup = BeautifulSoup(html, "html.parser")
        
        nombre_real = ""
        h1_tag = soup.find("h1")
        if h1_tag: nombre_real = h1_tag.get_text(strip=True)

        estado = "Disponible"
        presale_flag = soup.find(attrs={"data-testid": "flag-presale"})
        if presale_flag and "preventa" in presale_flag.get_text(strip=True).lower(): estado = "Preventa"
        else:
            for sp in soup.find_all("span"):
                if sp.get_text(strip=True).lower() == "preventa":
                    estado = "Preventa"; break

        def _limpiar_precio(tag):
            if not tag: return 0.0
            try: return float(re.sub(r'[^\d.]', '', tag.get_text(separator="", strip=True)))
            except: return 0.0
        
        p_act = _limpiar_precio(soup.find(attrs={"data-testid": "discounted"}))
        p_orig = _limpiar_precio(soup.find(attrs={"data-testid": "original"}))
        
        marca = ""
        brand_tag = soup.find("a", class_=lambda c: c and "ml-product-info-brand-link" in c)
        if brand_tag: marca = brand_tag.get_text(strip=True)
            
        categoria = ""
        breadcrumb_nav = soup.find("nav", attrs={"data-testid": lambda x: x and str(x).endswith("-breadcrumb")})
        if breadcrumb_nav:
            cat_links = breadcrumb_nav.find_all("a", href=re.compile(r"/tienda/.*?/cat"))
            if cat_links: categoria = cat_links[0].get_text(strip=True) or cat_links[0].get("aria-label", "")

        if p_act == 0.0 or not marca or not categoria or not nombre_real:
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get("@type") == "Product":
                        if p_act == 0.0 and "price" in data.get("offers", {}): p_act = float(data["offers"]["price"])
                        if not marca:
                            bd = data.get("brand")
                            marca = bd.get("name", "") if isinstance(bd, dict) else (bd if isinstance(bd, str) else "")
                        if not nombre_real: nombre_real = data.get("name", "")
                    if not categoria:
                        for item in (data if isinstance(data, list) else [data]):
                            if isinstance(item, dict) and item.get("@type") == "BreadcrumbList":
                                elems = item.get("itemListElement", [])
                                if len(elems) > 1: categoria = elems[1].get("item", {}).get("name", "")
                                elif len(elems) == 1: categoria = elems[0].get("item", {}).get("name", "")
                except: pass
        return p_act, p_orig, marca, categoria, nombre_real, estado

    @staticmethod
    def _variants_fixup(url: str) -> list[str]:
        cands = []
        if url.endswith(".jpg") and not url.endswith(".jpg.jpg"): cands.append(url + ".jpg")
        if url.endswith(".jpg.jpg"): cands.append(url[:-4])
        return cands

    @lru_cache(maxsize=8192)
    def resolver_producto(self, sku: str, usar_google: bool = True) -> tuple[list[str], str, str, str, float, float, str, str, str]:
        clean_sku = normalize_sku(sku)
        if not clean_sku: return [""]*6, "", "", "invalid-sku", 0.0, 0.0, "", "", "Disponible"

        urls_a_probar = [f"{BASE_PDP}/default/{clean_sku}"]
        slug = self.buscar_slug_por_google(clean_sku) if usar_google else ""
        if not slug: slug = self.buscar_slug_en_liverpool(clean_sku)
        if slug: urls_a_probar.extend([f"{BASE_PDP}/{slug}/{clean_sku}", f"{BASE_PDP}/{slug}/"])
        urls_a_probar.extend(self.candidatos_pdp_desde_busqueda(clean_sku))

        producto_url, imagenes_url, estrategia = "", [""]*6, "fallback"

        for url in urls_a_probar:
            cands = self.extraer_imagenes_de_html(self._get_html(url), clean_sku)
            if cands[0]:
                producto_url, imagenes_url, estrategia = url, cands, ("slug+sku" if url.endswith(f"/{clean_sku}") else "slug")
                break

        if not imagenes_url[0]:
            html_busq = self._get_html(f"{BASE_HOME}/tienda?s={clean_sku}")
            if html_busq:
                if 'data-testid="null-search-landing"' in html_busq or 'search-not-found-content' in html_busq:
                    estrategia = "offline / no encontrado"
                else:
                    cands = self.extraer_imagenes_de_html(html_busq, clean_sku)
                    if cands[0]:
                        imagenes_url, producto_url, estrategia = cands, f"{BASE_HOME}/tienda?s={clean_sku}", "busqueda"

        if estrategia == "offline / no encontrado":
            return [""]*6, "", "", estrategia, 0.0, 0.0, "", "", "Disponible"

        def _valid_or_fix(u: str) -> tuple[str, str]:
            if not u: return "", ""
            if self._check_image_validity(u): return u, "valid"
            for v in self._variants_fixup(u):
                if self._check_image_validity(v): return v, "fixup"
            return "", ""

        if imagenes_url[0]:
            fixed, tag = _valid_or_fix(imagenes_url[0])
            if fixed: imagenes_url[0], estrategia = fixed, tag if tag != "valid" else estrategia
            elif len(imagenes_url) > 1 and imagenes_url[1]:
                fixed_var, _ = _valid_or_fix(imagenes_url[1])
                if fixed_var: imagenes_url[0], estrategia = fixed_var, "promoted_variant"
        
        if not imagenes_url[0]:
            fallback = f"{BASE_IMG_FALLBACK}{clean_sku}.jpg"
            if self._check_image_validity(fallback): imagenes_url[0], estrategia = fallback, "fallback"
            else: estrategia = "no-image"

        producto_nombre = slug_a_nombre(slug)
        if not producto_url and slug: producto_url = f"{BASE_PDP}/{slug}/"

        p_actual, p_original, marca, categoria, nombre_real, estado = 0.0, 0.0, "", "", "", "Disponible"
        if producto_url:
            p_actual, p_original, marca, categoria, nombre_real, estado = self.extraer_datos_pdp(producto_url)

        if nombre_real: producto_nombre = nombre_real

        return imagenes_url, producto_url, producto_nombre, estrategia, p_actual, p_original, marca, categoria, estado

# ====================== ZIP & UI Helpers ======================

def generate_master_zip(df, progress=gr.Progress()):
    if df is None or df.empty: raise gr.Error("No hay datos para generar el ZIP.")
    ts = int(time.time())
    zip_filename = f"IMAGENES_LIVERPOOL_V8_6_{ts}.zip"
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    total_rows = len(df)
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for idx, row in df.iterrows():
            progress((idx + 1) / total_rows, desc=f"Descargando producto {idx+1}/{total_rows}")
            grupo = _coerce_nonempty_str(row.get("Grupo_Pegado", "General"))
            nombre = _coerce_nonempty_str(row.get("Producto_Nombre", "Producto"))
            sku = _coerce_nonempty_str(row.get("Producto", "SKU"))
            cl_grupo = re.sub(r'[\\/*?:"<>|]', "", grupo).strip()
            cl_nombre = re.sub(r'[\\/*?:"<>|]', "", nombre).strip()
            folder_name = f"{cl_grupo}/{cl_nombre} - {sku}"
            for i in range(1, 7):
                img_col = f"Image_{i}"
                if img_col in row and str(row[img_col]).startswith("http"):
                    url = str(row[img_col])
                    try:
                        r = session.get(url, timeout=10)
                        if r.status_code == 200:
                            ext = url.split('.')[-1].split('?')[0]
                            if len(ext) > 4 or not ext: ext = "jpg"
                            zipf.writestr(f"{folder_name}/imagen_{i}.{ext}", r.content)
                    except: pass
    return gr.update(value=zip_filename, visible=True)

def generate_inline_spinner(pct, done, total, eta_str):
    return f"""
    <div style="display: flex; align-items: center; justify-content: center; padding: 25px; margin-top: 15px; background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 8px;">
        <div style="display: flex; flex-direction: column; align-items: center;">
            <div class="loader" style="border: 4px solid #e2e8f0; border-top: 4px solid #3b82f6; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite;"></div>
            <div style="margin-top: 12px; font-size: 15px; font-weight: 800; color: #334155;">Procesando... {pct}%</div>
            <div style="font-size: 12px; font-weight: 600; color: #64748b; margin-top: 4px;">Extrayendo {done} de {total} productos</div>
            <div style="font-size: 11px; font-weight: bold; color: #94a3b8; margin-top: 4px;">Tiempo restante: {eta_str}</div>
        </div>
        <style>@keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}</style>
    </div>
    """

def build_html_gallery(df: pd.DataFrame, spinner_html: str = "") -> str:
    if df is None or df.empty and not spinner_html: return ""
    cols = {c.lower(): c for c in df.columns} if df is not None and not df.empty else {}
    img_cols = [c for i in range(1, 7) for c in [cols.get(f"image_{i}"), cols.get(f"image{i}")] if c]

    html_blocks = ['<div style="display: flex; flex-direction: column; gap: 1.5rem; padding: 10px;">']

    if df is not None and not df.empty:
        for _, row in df.iterrows():
            sku = _coerce_nonempty_str(row.get(cols.get("producto"), ""))
            name = _coerce_nonempty_str(row.get(cols.get("producto_nombre"), ""))
            url = _coerce_nonempty_str(row.get(cols.get("producto_url"), ""))
            marca = _coerce_nonempty_str(row.get(cols.get("marca"), ""))
            categoria = _coerce_nonempty_str(row.get(cols.get("categoria"), ""))
            grupo_pegado = _coerce_nonempty_str(row.get(cols.get("grupo_pegado"), "General"))
            estado = _coerce_nonempty_str(row.get(cols.get("estado"), "Disponible"))
            
            prefix = f"<span style='color: #4338ca; background-color: #e0e7ff; padding: 2px 8px; border-radius: 4px; margin-right: 8px;'>[{grupo_pegado}]</span>" if grupo_pegado != "General" else ""
            title = f"{prefix}{name} (SKU: {sku})" if name else f"{prefix}SKU: {sku}"
            
            valid_imgs = [row.get(c, "") for c in img_cols if str(row.get(c, "")).startswith("http")]
            if not valid_imgs: continue
            
            badge_text = f"Se encontraron {len(valid_imgs)} imágenes"
            urls_str = "|".join(valid_imgs)
            folder_name_safe = re.sub(r'[\\/*?:"<>|\']', "", f"{grupo_pegado + ' - ' if grupo_pegado != 'General' else ''}{name} - {sku}").replace('"', '').replace("'", "").strip()
            
            actions_html = f"""
            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
                {f'<a href="{url}" target="_blank" style="text-decoration: none; background-color: #f3e8ff; color: #7e22ce; padding: 6px 12px; border-radius: 9999px; font-size: 13px; font-weight: bold; border: 1px solid #e9d5ff;">🛒 Ver en tienda</a>' if url else ''}
                <a href="#" class="dl-zip-btn" data-folder="{folder_name_safe}" data-urls="{urls_str}" style="text-decoration: none; background-color: #e0f2fe; color: #0284c7; padding: 6px 12px; border-radius: 9999px; font-size: 13px; font-weight: bold; border: 1px solid #bae6fd;">📥 Descargar Imágenes</a>
            </div>
            """

            estado_html = f'<span style="background-color: #cffafe; color: #0891b2; padding: 2px 6px; border-radius: 4px; font-weight: 700;">{estado}</span>' if estado.lower() == "preventa" else f'<span style="background-color: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 4px; font-weight: 700;">{estado}</span>'
            
            metadata_html = f"""<div style="display: flex; flex-direction: column; gap: 6px; margin-top: 6px; font-size: 13px;">
                <div style="color: #334155; font-weight: 700;">⚡ Estado: {estado_html}</div>
                {f'<div style="color: #334155; font-weight: 700;">📂 Categoría web: <span style="color: #0f172a; font-weight: 900;">{categoria}</span></div>' if categoria else ''}
                {f'<div style="color: #334155; font-weight: 700;">🏷️ Marca: <span style="color: #0f172a; font-weight: 900;">{marca}</span></div>' if marca else ''}
            </div>"""

            p_act_val = float(row.get(cols.get("precio_actual"), 0.0) or 0.0)
            p_orig_val = float(row.get(cols.get("precio_original"), 0.0) or 0.0)
            pct = str(row.get(cols.get("descuento_porcentaje"), "0%"))
                
            prices_html = ""
            if p_act_val > 0:
                if p_orig_val > p_act_val:
                    prices_html = f"""<div style="margin-top: auto; border-top: 1px solid #e5e7eb; padding-top: 12px; display: flex; flex-direction: column; gap: 6px;">
                        <div style="display: flex; justify-content: space-between; font-size: 13px;"><span style="color: #6b7280;">Precio Original:</span> <span style="text-decoration: line-through; color: #9ca3af;">${p_orig_val:,.2f}</span></div>
                        <div style="display: flex; justify-content: space-between; font-size: 14px;"><span style="color: #4b5563; font-weight: 600;">Precio Actual:</span> <span style="color: #e11d48; font-size: 18px; font-weight: 800;">${p_act_val:,.2f}</span></div>
                        <div style="text-align: right; margin-top: 4px;"><span style="background-color: #fef2f2; color: #dc2626; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; border: 1px solid #fecaca;">-{pct} DESC.</span></div>
                    </div>"""
                else:
                    prices_html = f"""<div style="margin-top: auto; border-top: 1px solid #e5e7eb; padding-top: 12px; display: flex; justify-content: space-between; font-size: 14px;">
                        <span style="color: #4b5563; font-weight: 600;">Precio:</span> <span style="color: #1f2937; font-size: 18px; font-weight: 800;">${p_act_val:,.2f}</span>
                    </div>"""
                
            box_html = f"""<div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 8px; align-items: stretch;">
                <div style="flex: 3 1 500px; border: 1px solid #d1d5db; border-radius: 8px; padding: 16px; background-color: #f8fafc; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <h4 style="margin: 0 0 16px 0; color: #4c1d95; font-size: 16px; font-weight: bold;">📦 {title}</h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 12px;">"""
            for idx, img in enumerate(valid_imgs):
                box_html += f'<div style="width: 150px; height: 200px; border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden; display: flex; justify-content: center; align-items: center; background: #ffffff;"><img src="{img}" style="max-width: 100%; max-height: 100%; object-fit: contain;"/></div>'
            box_html += f"""</div></div>
                <div style="flex: 1 1 250px; border: 1px solid #d1d5db; border-radius: 8px; padding: 16px; background-color: #f8fafc; box-shadow: 0 1px 3px rgba(0,0,0,0.1); display: flex; flex-direction: column; justify-content: space-between;">
                    <div>{actions_html}<span style="background-color: #e0e7ff; color: #4338ca; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: bold; border: 1px solid #c7d2fe;">📸 {badge_text}</span>{metadata_html}</div>
                    {prices_html}
                </div></div>"""
            html_blocks.append(box_html)
            
    if spinner_html:
        html_blocks.append(spinner_html)
        
    html_blocks.append('</div>')
    return "\n".join(html_blocks)

# V8.6 NUEVO: Tarjeta Amarilla de Duplicados
def generate_duplicates_html(duplicates_dict: dict) -> str:
    if not duplicates_dict: return ""
    count = sum(len(skus) for skus in duplicates_dict.values())
    
    lines_html = ""
    for g, skus in duplicates_dict.items():
        g_name = g if str(g).strip() and str(g)!='General' else 'Sin Categoría'
        lines_html += f'<div style="color: #854d0e;"><strong style="color: #854d0e;">[{g_name}]:</strong> {", ".join(skus)}</div>'
        
    return f"""
    <div style="background: linear-gradient(to right, #fefce8, #fef9c3); border-left: 6px solid #eab308; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px;">
        <h3 style="margin: 0 0 8px 0; color: #854d0e; font-size: 18px; font-weight: bold; display: flex; align-items: center; gap: 8px;">
            ⚠️ PRODUCTOS REPETIDOS / Omitidos: {count}
        </h3>
        <p style="margin: 0 0 12px 0; color: #a16207; font-size: 14px;">
            Estos SKUs ya estaban en la lista y fueron omitidos para evitar duplicados en el entregable:
        </p>
        <div style="display: flex; flex-direction: column; gap: 6px; font-size: 14px;">
            {lines_html}
        </div>
    </div>
    """

def generate_offline_html(offline_dict: dict) -> str:
    if not offline_dict: return ""
    count = sum(len(skus) for skus in offline_dict.values())
    
    lines_html = ""
    for g, skus in offline_dict.items():
        g_name = g if str(g).strip() and str(g)!='General' else 'Sin Categoría'
        lines_html += f'<div style="color: #7f1d1d;"><strong style="color: #7f1d1d;">[{g_name}]:</strong> {", ".join(skus)}</div>'
        
    return f"""
    <div style="background: linear-gradient(to right, #fef2f2, #fee2e2); border-left: 6px solid #ef4444; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px;">
        <h3 style="margin: 0 0 8px 0; color: #7f1d1d; font-size: 18px; font-weight: bold; display: flex; align-items: center; gap: 8px;">
            ⚠️ PRODUCTOS OFF / Descatalogados: {count}
        </h3>
        <p style="margin: 0 0 12px 0; color: #991b1b; font-size: 14px;">
            Estos SKUs no arrojaron resultados y <strong style="color: #7f1d1d;">NO se agregaron al CSV</strong>:
        </p>
        <div style="display: flex; flex-direction: column; gap: 6px; font-size: 14px;">
            {lines_html}
        </div>
    </div>
    """

def _preview_with_toggles(full_df: pd.DataFrame, show_url: bool, show_name: bool, show_strategy: bool) -> pd.DataFrame:
    cols = ["ID", "Grupo_Pegado", "Producto", "Categoria", "Marca", "Estado", "Precio_Actual", "Precio_Original", "Descuento_Porcentaje", "Image_1", "Image_2", "Image_3", "Image_4", "Image_5", "Image_6"]
    if show_url: cols.append("producto_url")
    if show_name: cols.append("Producto_Nombre")
    if show_strategy: cols.append("Estrategia")
    return full_df.loc[:, [c for c in cols if c in full_df.columns]]

def _write_csvs(full_df: pd.DataFrame, prefix: str) -> str:
    csv_cols = ["ID", "Grupo_Pegado", "Producto", "Categoria", "Marca", "Estado", "Precio_Actual", "Precio_Original", "Descuento_Porcentaje", "Image_1", "Image_2", "Image_3", "Image_4", "Image_5", "Image_6"]
    df_export = full_df.loc[:, [c for c in csv_cols if c in full_df.columns]] if not full_df.empty else pd.DataFrame(columns=csv_cols)
    fp = f"{prefix}_FEED_{int(time.time())}.csv"
    df_export.to_csv(fp, index=False, encoding="utf-8")
    return fp

HEAD_JS = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
<script>
document.addEventListener('click', async function(e) {
    const path = e.composedPath ? e.composedPath() : (e.path || [e.target]);
    let btn = null;
    for (let i = 0; i < path.length; i++) {
        if (path[i] && path[i].classList && path[i].classList.contains('dl-zip-btn')) { btn = path[i]; break; }
    }
    if (!btn) return;
    e.preventDefault();
    if (typeof window.JSZip === 'undefined') { alert("Las librerías del ZIP aún están cargando. Intenta de nuevo en 1 segundo."); return; }
    const originalText = btn.innerHTML;
    btn.innerHTML = "⏳ Descargando...";
    btn.style.pointerEvents = "none"; btn.style.opacity = "0.7";
    try {
        const urls = btn.getAttribute('data-urls').split('|').filter(u => u.trim() !== '');
        const folderName = btn.getAttribute('data-folder');
        const zip = new window.JSZip(); const folder = zip.folder(folderName);
        let downloaded = 0;
        for(let i=0; i<urls.length; i++) {
            let url = urls[i], blob = null;
            try { let resp = await fetch(url); if (!resp.ok) throw new Error("Status"); blob = await resp.blob(); }
            catch(err) { try { let resp = await fetch('https://corsproxy.io/?' + encodeURIComponent(url)); if (resp.ok) blob = await resp.blob(); } catch(err2) { } }
            if (blob) { let ext = url.split('.').pop().split('?')[0]; folder.file("imagen_" + (i+1) + "." + (ext.length > 4 || !ext ? 'jpg' : ext), blob); downloaded++; }
        }
        if (downloaded === 0 && urls.length > 0) alert("No se pudo descargar ninguna imagen por bloqueos del navegador.\\n\\nSolución: Usa el botón '📦 Generar ZIP' superior.");
        else {
            const content = await zip.generateAsync({type:"blob"});
            const link = document.createElement('a'); link.href = URL.createObjectURL(content);
            link.download = folderName + ".zip"; document.body.appendChild(link); link.click();
            document.body.removeChild(link); setTimeout(() => URL.revokeObjectURL(link.href), 2000);
        }
    } catch(err) { alert("Ocurrió un error al crear el archivo ZIP."); }
    btn.innerHTML = originalText; btn.style.pointerEvents = "auto"; btn.style.opacity = "1";
});
</script>
"""

client = LiverpoolClient()

# ====================== Motor Central ======================

# V8.6 FIX: core_engine ahora acepta y despacha "duplicates_dict"
def core_engine(parsed_skus, duplicates_dict, delay_val, usar_google_val, show_url_val, show_name_val, show_strategy_val, prefix="ENTREGABLE"):
    
    total = len(parsed_skus)
    initial_spinner = generate_inline_spinner(0, 0, total, "Calculando...")
    
    yield (
        gr.update(), gr.update(), gr.update(), 
        gr.update(value=build_html_gallery(pd.DataFrame(), spinner_html=initial_spinner)), 
        gr.update(value=pd.DataFrame()), gr.update(), gr.update(value=None, visible=False)
    )

    valid_records, offline_dict = [], {}
    t0 = time.monotonic()

    for idx, (grupo, sku) in enumerate(parsed_skus):
        imgs, purl, pname, strat, p_actual, p_original, marca, categoria, estado = client.resolver_producto(sku, usar_google=usar_google_val)
        
        is_offline = (strat == "offline / no encontrado") or (not imgs[0] and not pname)
        if is_offline:
            if grupo not in offline_dict: offline_dict[grupo] = []
            if sku not in offline_dict[grupo]: offline_dict[grupo].append(sku)
        else:
            pct_desc = int(round((1 - p_actual / p_original) * 100)) if p_original > p_actual > 0 else 0
            valid_records.append({
                "ID": len(valid_records) + 1, "Grupo_Pegado": grupo, "Producto": sku, "Categoria": categoria, "Marca": marca, "Estado": estado,
                "Precio_Actual": p_actual, "Precio_Original": p_original, "Descuento_Porcentaje": f"{pct_desc}%" if pct_desc > 0 else "0%",
                "Image_1": imgs[0], "Image_2": imgs[1], "Image_3": imgs[2], "Image_4": imgs[3], "Image_5": imgs[4], "Image_6": imgs[5],
                "producto_url": purl, "Producto_Nombre": pname, "Estrategia": strat,
            })

        if delay_val > 0: time.sleep(delay_val + random.uniform(0.05, 0.25))
        done = idx + 1
        elapsed = max(1e-6, time.monotonic() - t0)
        rate = done / elapsed
        eta = (total - done) / rate if rate > 0 else None
        
        pct_num = int(done * 100 / total)
        eta_str = f"~{fmt_duration(eta)}" if eta is not None else "Calculando..."

        temp_df = pd.DataFrame(valid_records)
        current_spinner = generate_inline_spinner(pct_num, done, total, eta_str)
        temp_gallery = build_html_gallery(temp_df, spinner_html=current_spinner)
        temp_preview = _preview_with_toggles(temp_df, show_url_val, show_name_val, show_strategy_val) if not temp_df.empty else pd.DataFrame()
        
        yield (
            gr.update(), gr.update(), gr.update(), 
            gr.update(value=temp_gallery), 
            gr.update(value=temp_preview), 
            temp_df, 
            gr.update(value=None, visible=False)
        )

    # FINALIZACIÓN
    final_df = pd.DataFrame(valid_records)
    feed_path = _write_csvs(final_df, f"{prefix}_V8_6")
    
    success_card = f"""
    <div style="background: linear-gradient(to right, #ecfdf5, #d1fae5); border-left: 6px solid #10b981; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0; color: #064e3b; font-size: 20px; font-weight: bold; display: flex; align-items: center; gap: 8px;">
            🎉 ¡Entregable Listo y Procesado Exitosamente!
        </h3>
        <div style="display: flex; gap: 20px; font-size: 15px;">
            <div style="color: #064e3b;"><strong style="color: #064e3b;">SKUs Validados:</strong> <span style="background: #a7f3d0; padding: 2px 8px; border-radius: 4px; color: #064e3b; font-weight: bold;">{len(valid_records)}</span></div>
            <div style="color: #064e3b;"><strong style="color: #064e3b;">Categorías Detectadas:</strong> <span style="background: #a7f3d0; padding: 2px 8px; border-radius: 4px; color: #064e3b; font-weight: bold;">{final_df['Grupo_Pegado'].nunique() if not final_df.empty else 0}</span></div>
        </div>
    </div>
    """
    
    yield (
        gr.update(value=success_card, visible=True),
        gr.update(value=generate_duplicates_html(duplicates_dict), visible=True),
        gr.update(value=generate_offline_html(offline_dict), visible=True),
        gr.update(value=build_html_gallery(final_df, spinner_html="")), 
        gr.update(value=_preview_with_toggles(final_df, show_url_val, show_name_val, show_strategy_val)),
        final_df, 
        gr.update(value=NOTIFY_SOUND, visible=True)
    )

# ====================== Interfaz de Usuario ======================

try: THEME = gr.themes.Soft(primary_hue="fuchsia", secondary_hue="violet", neutral_hue="slate")
except: THEME = gr.themes.Soft()
CUSTOM_CSS = ".download-row .wrap { gap: 8px !important; align-items: center; }"

with gr.Blocks(theme=THEME, css=CUSTOM_CSS, head=HEAD_JS, title="V8.6 – Generador de Entregable") as demo:
    df_state = gr.State()
    
    gr.Markdown("### V8.6 – Tarjetas Inteligentes (Éxito, Repetidos, Descatalogados)")

    with gr.Tabs():
        with gr.TabItem("📝 Pegar SKUs / Excel"):
            skus_in = gr.Textbox(lines=5, label="Pega tu tabla (Categoría + SKUs mezclados)", placeholder="Zapatos\t12501544\t14152211")
            btn_proc_paste = gr.Button("⚙️ Procesar Tabla Manual", variant="primary")
            
        with gr.TabItem("🔍 Extraer Destacados (Automático)"):
            gr.Markdown("Selecciona la categoría para extraer los productos destacados directamente de la tienda.")
            with gr.Row():
                cat_n1 = gr.Dropdown(label="Categoría Principal", choices=list(CATALOGO_LIVERPOOL.keys()), value="Mujer")
                cat_n2 = gr.Dropdown(label="Subcategoría 1", choices=list(CATALOGO_LIVERPOOL["Mujer"].keys()))
                cat_n3 = gr.Dropdown(label="Subcategoría 2", choices=list(CATALOGO_LIVERPOOL["Mujer"].get("Ropa", {}).keys()))
            
            limit_destacados = gr.Number(label="Cantidad máxima a extraer", value=50, precision=0, minimum=1, maximum=200)
            btn_proc_cat = gr.Button("🚀 Extraer y Procesar Destacados", variant="primary")

    with gr.Accordion("⚙️ Ajustes de Procesamiento (Avanzado)", open=False):
        with gr.Row():
            delay_global = gr.Slider(0.0, 2.0, value=0.3, step=0.1, label="Delay entre requests (seg)")
            google_global = gr.Checkbox(value=True, label="Usar Google (más preciso)")
        with gr.Row():
            show_url_global = gr.Checkbox(value=True, label="Mostrar producto_url (vista previa)")
            show_name_global = gr.Checkbox(value=True, label="Mostrar Producto_Nombre (vista previa)")
            show_strat_global = gr.Checkbox(value=False, label="Mostrar Estrategia (vista previa)")

    gr.Markdown("---")
    
    out_stats_shared = gr.HTML(visible=False) 
    out_duplicates_shared = gr.HTML(visible=False) # NUEVA TARJETA AMARILLA AÑADIDA A LA UI
    out_broken_md_shared = gr.HTML(visible=False) 

    with gr.Column(elem_classes=["download-row"]):
        with gr.Row():
            download_feed_shared = gr.DownloadButton("⬇️ DESCARGAR CSV FEED", visible=False, variant="primary")
            btn_master_zip = gr.Button("📦 Generar ZIP de Imágenes", visible=False, variant="secondary")
            download_master_zip = gr.DownloadButton("⬇️ DESCARGAR ZIP MAESTRO", visible=False, variant="primary")
    
    gr.Markdown("---")
    gr.Markdown("### 🖼️ Preview de imágenes y Datos")
    out_gallery_shared = gr.HTML(label="Preview de imágenes")
    gr.Markdown("### 📊 Vista previa entregable")
    out_preview_shared = gr.Dataframe(interactive=False, wrap=True, label="Vista previa entregable")
    notif_audio = gr.Audio(label="🔔 Notificación", autoplay=True, interactive=False, visible=False)

    def update_n2(n1):
        if not n1: return gr.update(choices=[], value=None)
        opts = list(CATALOGO_LIVERPOOL.get(n1, {}).keys())
        return gr.update(choices=opts, value=opts[0] if opts else None)

    def update_n3(n1, n2):
        if not n1 or not n2: return gr.update(choices=[], value=None)
        sub = CATALOGO_LIVERPOOL.get(n1, {}).get(n2, {})
        opts = list(sub.keys())
        return gr.update(choices=opts, value=opts[0] if opts else None)

    cat_n1.change(fn=update_n2, inputs=[cat_n1], outputs=[cat_n2]).then(fn=update_n3, inputs=[cat_n1, cat_n2], outputs=[cat_n3])
    cat_n2.change(fn=update_n3, inputs=[cat_n1, cat_n2], outputs=[cat_n3])

    def handler_paste(skus_text, delay, use_g, s_url, s_name, s_strat):
        parsed, duplicates = parse_grouped_skus(skus_text)
        if not parsed: raise gr.Error("No se encontraron SKUs válidos.")
        yield from core_engine(parsed, duplicates, delay, use_g, s_url, s_name, s_strat, "MANUAL")

    def handler_extract(n1, n2, n3, limit, delay, use_g, s_url, s_name, s_strat):
        if not n1 or not n2 or not n3: raise gr.Error("Selecciona la jerarquía completa de categorías.")
        url = CATALOGO_LIVERPOOL.get(n1, {}).get(n2, {}).get(n3, "")
        if not url: raise gr.Error("No se encontró la URL en el catálogo.")
        
        yield (gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(value=""), gr.update(value=pd.DataFrame()), gr.update(), gr.update(value=None, visible=False))
        
        skus = client.extraer_skus_de_categoria(url, limit=int(limit))
        if not skus: raise gr.Error("No se lograron extraer productos. La categoría podría estar vacía.")
        
        grupo_nombre = f"{n1} - {n3}"
        parsed = [(grupo_nombre, sku) for sku in skus]
        yield from core_engine(parsed, {}, delay, use_g, s_url, s_name, s_strat, "DESTACADOS")

    btn_proc_paste.click(
        fn=handler_paste,
        inputs=[skus_in, delay_global, google_global, show_url_global, show_name_global, show_strat_global],
        # V8.6 FIX: Se agrega la variable "out_duplicates_shared" al array de salidas
        outputs=[out_stats_shared, out_duplicates_shared, out_broken_md_shared, out_gallery_shared, out_preview_shared, df_state, notif_audio],
        show_progress="hidden"
    ).then(
        fn=lambda: (gr.update(visible=True), gr.update(visible=True)), 
        outputs=[download_feed_shared, btn_master_zip]
    )

    btn_proc_cat.click(
        fn=handler_extract,
        inputs=[cat_n1, cat_n2, cat_n3, limit_destacados, delay_global, google_global, show_url_global, show_name_global, show_strat_global],
        # V8.6 FIX: Se agrega la variable "out_duplicates_shared" al array de salidas
        outputs=[out_stats_shared, out_duplicates_shared, out_broken_md_shared, out_gallery_shared, out_preview_shared, df_state, notif_audio],
        show_progress="hidden"
    ).then(
        fn=lambda: (gr.update(visible=True), gr.update(visible=True)), 
        outputs=[download_feed_shared, btn_master_zip]
    )

    def pre_zip_ui(): return gr.update(value="⏳ ✨ Empacando imágenes...", interactive=False)
    def post_zip_ui(): return gr.update(value="📦 Generar ZIP de Imágenes", interactive=True)

    btn_master_zip.click(fn=pre_zip_ui, inputs=[], outputs=[btn_master_zip]).then(
        fn=generate_master_zip, inputs=[df_state], outputs=[download_master_zip]
    ).then(fn=post_zip_ui, inputs=[], outputs=[btn_master_zip])

if __name__ == "__main__":
    demo.launch()
# app.py – V8.7 Maestro Distribuido (E-commerce Minimalist UI + 10 Motores)
import os
import re
import time
import random
import json
import zipfile
import typing as t
import concurrent.futures
from urllib.parse import unquote

import pandas as pd
import gradio as gr
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter, Retry

# ============================ Motores Preconfigurados ============================

DEFAULT_WORKERS = (
    "https://motor-liv1.onrender.com"
)

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

BASE_HOME = "https://www.liverpool.com.mx"
WORKER_TIMEOUT = 120
NOTIFY_SOUND = os.environ.get("CUSTOM_NOTIFY_SOUND", "notify.mp3")

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
                        if current_category not in duplicates:
                            duplicates[current_category] = []
                        duplicates[current_category].append(sku)
            else:
                clean_text = p.strip(' \t\n\r,-:|')
                if clean_text and re.search(r'[^\W\d_]', clean_text):
                    current_category = re.sub(r'\s+', ' ', clean_text)
    return out, duplicates

# ============================ Extractor de Categorías (Maestro) ============================

def extraer_skus_de_categoria_maestro(url: str, limit: int = 50) -> list[str]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "es-MX,es;q=0.9",
            "Referer": BASE_HOME,
        }
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200 or not r.text: return []
        html = r.text
        skus = []
        soup = BeautifulSoup(html, "html.parser")
        
        script_next = soup.find("script", id="__NEXT_DATA__")
        if script_next:
            try:
                data = json.loads(script_next.string)
                records = data.get("props", {}).get("pageProps", {}).get("initialState", {}).get("plp", {}).get("plpState", {}).get("records", [])
                for rec in records:
                    sku = rec.get("productId")
                    if sku and sku not in skus: skus.append(sku)
                if skus: return skus[:limit]
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
    except Exception:
        return []

# ====================== Orquestador Distribuido ======================

def consultar_worker(worker_url: str, item_sku: tuple[str, str]) -> dict:
    url = worker_url.strip().rstrip("/") + "/procesar_lote"
    payload = {"skus": [list(item_sku)], "usar_google": True}
    for intento in range(2):
        try:
            resp = requests.post(url, json=payload, timeout=WORKER_TIMEOUT)
            if resp.status_code == 200: return resp.json()
        except Exception:
            time.sleep(1)
    grupo, sku = item_sku
    return {"valid_records": [], "offline": {grupo: [sku]}}

def core_engine_distribuido(parsed_skus, duplicates_dict, workers_str, delay_val, usar_google_val, show_url_val, show_name_val, show_strategy_val, prefix="ENTREGABLE"):
    total = len(parsed_skus)
    workers = [w.strip() for w in workers_str.split(",") if w.strip()]
    if not workers: raise gr.Error("Configura al menos una URL de Motor válida.")
    
    num_workers = len(workers)
    initial_spinner = generate_inline_spinner(0, 0, total, f"Conectando con {num_workers} motores...")
    
    yield (
        gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), 
        gr.update(value=build_html_gallery(pd.DataFrame(), spinner_html=initial_spinner)), 
        gr.update(value=pd.DataFrame()), gr.update(), gr.update(value=None, visible=False)
    )

    valid_records, offline_dict = [], {}
    t0 = time.monotonic()
    done = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        for wave_start in range(0, total, num_workers):
            wave_items = parsed_skus[wave_start:wave_start + num_workers]
            futures_in_order = [
                executor.submit(consultar_worker, workers[idx], item)
                for idx, item in enumerate(wave_items)
            ]
            
            for future in futures_in_order:
                res = future.result()
                batch_valid = res.get("valid_records", [])
                batch_offline = res.get("offline", {})
                
                for rec in batch_valid:
                    rec["ID"] = len(valid_records) + 1
                    valid_records.append(rec)
                    
                for grupo, skus_list in batch_offline.items():
                    if grupo not in offline_dict: offline_dict[grupo] = []
                    for s in skus_list:
                        if s not in offline_dict[grupo]: offline_dict[grupo].append(s)

            done += len(wave_items)
            if delay_val > 0: time.sleep(delay_val)

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

    final_df = pd.DataFrame(valid_records)
    feed_path = _write_csvs(final_df, f"{prefix}_V8_7")
    
    success_card = f"""
    <div style="background: linear-gradient(to right, #ecfdf5, #d1fae5); border-left: 6px solid #10b981; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0; color: #064e3b; font-size: 18px; font-weight: bold;">🎉 ¡Procesamiento Exitoso ({num_workers} Motores)!</h3>
        <div style="display: flex; gap: 15px; font-size: 14px; flex-wrap: wrap; color: #064e3b;">
            <div><strong>SKUs Validados:</strong> {len(valid_records)}</div>
            <div><strong>Tiempo Total:</strong> {fmt_duration(time.monotonic() - t0)}</div>
        </div>
    </div>
    """
    
    yield (
        gr.update(value=success_card, visible=True),
        gr.update(value=generate_duplicates_html(duplicates_dict), visible=bool(duplicates_dict)),
        gr.update(value=generate_offline_html(offline_dict), visible=bool(offline_dict)),
        gr.update(value=build_html_gallery(final_df, spinner_html="")), 
        gr.update(value=_preview_with_toggles(final_df, show_url_val, show_name_val, show_strategy_val)),
        final_df, 
        gr.update(value=NOTIFY_SOUND, visible=True),
        gr.update(value=feed_path, visible=True)
    )

# ====================== ZIP & UI Helpers ======================

def generate_master_zip(df, progress=gr.Progress()):
    if df is None or df.empty: raise gr.Error("No hay datos para generar el ZIP.")
    ts = int(time.time())
    zip_filename = f"IMAGENES_LIVERPOOL_V8_7_{ts}.zip"
    session = requests.Session()
    total_rows = len(df)
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for idx, row in df.iterrows():
            progress((idx + 1) / total_rows, desc=f"Descargando producto {idx+1}/{total_rows}")
            grupo = _coerce_nonempty_str(row.get("Grupo_Pegado", "General"))
            nombre = _coerce_nonempty_str(row.get("Producto_Nombre", "Producto"))
            sku = _coerce_nonempty_str(row.get("Producto", "SKU"))
            folder_name = f"{re.sub(r'[\\/*?:"<>|]', '', grupo)}/{re.sub(r'[\\/*?:"<>|]', '', nombre)} - {sku}"
            for i in range(1, 7):
                img_col = f"Image_{i}"
                if img_col in row and str(row[img_col]).startswith("http"):
                    try:
                        r = session.get(str(row[img_col]), timeout=10)
                        if r.status_code == 200:
                            zipf.writestr(f"{folder_name}/imagen_{i}.jpg", r.content)
                    except: pass
    return gr.update(value=zip_filename, visible=True)

def generate_inline_spinner(pct, done, total, eta_str):
    return f"""
    <div style="display: flex; align-items: center; justify-content: center; padding: 20px; margin-top: 10px; background: #ffffff; border: 1px dashed #d1d5db; border-radius: 8px;">
        <div style="display: flex; flex-direction: column; align-items: center;">
            <div class="loader" style="border: 3px solid #f3f4f6; border-top: 3px solid #111827; border-radius: 50%; width: 35px; height: 35px; animation: spin 1s linear infinite;"></div>
            <div style="margin-top: 10px; font-size: 14px; font-weight: 700; color: #111827;">Procesando con 10 Motores... {pct}%</div>
            <div style="font-size: 12px; color: #6b7280; margin-top: 2px;">Extrayendo {done} de {total} productos (ETA: {eta_str})</div>
        </div>
        <style>@keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}</style>
    </div>
    """

def build_html_gallery(df: pd.DataFrame, spinner_html: str = "") -> str:
    if df is None or df.empty and not spinner_html: return ""
    cols = {c.lower(): c for c in df.columns} if df is not None and not df.empty else {}
    img_cols = [c for i in range(1, 7) for c in [cols.get(f"image_{i}"), cols.get(f"image{i}")] if c]

    html_blocks = ['<div style="display: flex; flex-direction: column; gap: 1rem; padding: 5px;">']

    if df is not None and not df.empty:
        for _, row in df.iterrows():
            sku = _coerce_nonempty_str(row.get(cols.get("producto"), ""))
            name = _coerce_nonempty_str(row.get(cols.get("producto_nombre"), ""))
            url = _coerce_nonempty_str(row.get(cols.get("producto_url"), ""))
            marca = _coerce_nonempty_str(row.get(cols.get("marca"), ""))
            categoria = _coerce_nonempty_str(row.get(cols.get("categoria"), ""))
            grupo_pegado = _coerce_nonempty_str(row.get(cols.get("grupo_pegado"), "General"))
            estado = _coerce_nonempty_str(row.get(cols.get("estado"), "Disponible"))
            
            prefix = f"<span style='color: #4338ca; background-color: #e0e7ff; padding: 2px 6px; border-radius: 4px; margin-right: 6px; font-size: 12px;'>[{grupo_pegado}]</span>" if grupo_pegado != "General" else ""
            title = f"{prefix}{name} (SKU: {sku})" if name else f"{prefix}SKU: {sku}"
            
            valid_imgs = [row.get(c, "") for c in img_cols if str(row.get(c, "")).startswith("http")]
            if not valid_imgs: continue
            
            badge_text = f"{len(valid_imgs)} vistas"
            urls_str = "|".join(valid_imgs)
            folder_name_safe = re.sub(r'[\\/*?:"<>|\']', "", f"{grupo_pegado + ' - ' if grupo_pegado != 'General' else ''}{name} - {sku}").replace('"', '').replace("'", "").strip()
            
            actions_html = f"""
            <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px;">
                {f'<a href="{url}" target="_blank" style="text-decoration: none; background-color: #f3e8ff; color: #7e22ce; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;">🛒 Tienda</a>' if url else ''}
                <a href="#" class="dl-zip-btn" data-folder="{folder_name_safe}" data-urls="{urls_str}" style="text-decoration: none; background-color: #e0f2fe; color: #0284c7; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;">📥 ZIP Imgs</a>
            </div>
            """

            p_act_val = float(row.get(cols.get("precio_actual"), 0.0) or 0.0)
            p_orig_val = float(row.get(cols.get("precio_original"), 0.0) or 0.0)
            pct = str(row.get(cols.get("descuento_porcentaje"), "0%"))
                
            prices_html = ""
            if p_act_val > 0:
                if p_orig_val > p_act_val:
                    prices_html = f"""<div style="border-top: 1px solid #f3f4f6; padding-top: 8px; display: flex; flex-direction: column; gap: 4px; font-size: 12px;">
                        <div style="display: flex; justify-content: space-between;"><span style="color: #6b7280;">Orig:</span> <span style="text-decoration: line-through; color: #9ca3af;">${p_orig_val:,.2f}</span></div>
                        <div style="display: flex; justify-content: space-between;"><span style="color: #374151; font-weight: 600;">Actual:</span> <span style="color: #dc2626; font-weight: 700;">${p_act_val:,.2f}</span></div>
                    </div>"""
                else:
                    prices_html = f"""<div style="border-top: 1px solid #f3f4f6; padding-top: 8px; display: flex; justify-content: space-between; font-size: 12px;">
                        <span style="color: #374151; font-weight: 600;">Precio:</span> <span style="color: #111827; font-weight: 700;">${p_act_val:,.2f}</span>
                    </div>"""
                
            box_html = f"""<div style="display: flex; gap: 15px; flex-wrap: wrap; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; align-items: stretch;">
                <div style="flex: 3 1 450px;">
                    <h4 style="margin: 0 0 10px 0; color: #111827; font-size: 14px; font-weight: 600;">📦 {title}</h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px;">"""
            for img in valid_imgs:
                box_html += f'<div style="width: 90px; height: 120px; border: 1px solid #f3f4f6; border-radius: 4px; overflow: hidden; display: flex; justify-content: center; align-items: center; background: #fafafa;"><img src="{img}" style="max-width: 100%; max-height: 100%; object-fit: contain;"/></div>'
            box_html += f"""</div></div>
                <div style="flex: 1 1 200px; border-left: 1px solid #f3f4f6; padding-left: 12px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>{actions_html}<div style="font-size: 12px; color: #4b5563; margin-bottom: 4px;">🏷️ {marca or 'Genérica'}</div><div style="font-size: 12px; color: #4b5563;">⚡ {estado}</div></div>
                    {prices_html}
                </div></div>"""
            html_blocks.append(box_html)
            
    if spinner_html: html_blocks.append(spinner_html)
    html_blocks.append('</div>')
    return "\n".join(html_blocks)

def generate_duplicates_html(duplicates_dict: dict) -> str:
    if not duplicates_dict: return ""
    count = sum(len(skus) for skus in duplicates_dict.values())
    return f"""<div style="background: #fefce8; border-left: 4px solid #eab308; padding: 12px; border-radius: 6px; margin-bottom: 12px; font-size: 13px;">
        <strong style="color: #854d0e;">⚠️ Productos Repetidos / Omitidos ({count})</strong></div>"""

def generate_offline_html(offline_dict: dict) -> str:
    if not offline_dict: return ""
    count = sum(len(skus) for skus in offline_dict.values())
    return f"""<div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; border-radius: 6px; margin-bottom: 12px; font-size: 13px;">
        <strong style="color: #7f1d1d;">⚠️ Productos Descatalogados / Off ({count})</strong></div>"""

def _preview_with_toggles(full_df, show_url, show_name, show_strategy):
    cols = ["ID", "Grupo_Pegado", "Producto", "Categoria", "Marca", "Estado", "Precio_Actual", "Precio_Original", "Descuento_Porcentaje"]
    return full_df.loc[:, [c for c in cols if c in full_df.columns]]

def _write_csvs(full_df, prefix):
    fp = f"{prefix}_FEED_{int(time.time())}.csv"
    full_df.to_csv(fp, index=False, encoding="utf-8")
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
    if (typeof window.JSZip === 'undefined') { alert("Cargando librería ZIP..."); return; }
    const originalText = btn.innerHTML;
    btn.innerHTML = "⏳ Descargando...";
    try {
        const urls = btn.getAttribute('data-urls').split('|').filter(u => u.trim() !== '');
        const folderName = btn.getAttribute('data-folder');
        const zip = new window.JSZip(); const folder = zip.folder(folderName);
        let downloaded = 0;
        for(let i=0; i<urls.length; i++) {
            let url = urls[i], blob = null;
            try { let resp = await fetch(url); if (resp.ok) blob = await resp.blob(); } catch(err) {}
            if (blob) { folder.file("imagen_" + (i+1) + ".jpg", blob); downloaded++; }
        }
        if (downloaded > 0) {
            const content = await zip.generateAsync({type:"blob"});
            const link = document.createElement('a'); link.href = URL.createObjectURL(content);
            link.download = folderName + ".zip"; document.body.appendChild(link); link.click();
            document.body.removeChild(link);
        }
    } catch(err) {}
    btn.innerHTML = originalText;
});
</script>
"""

# ====================== Interfaz de Usuario (E-commerce Minimalista) ======================

THEME = gr.themes.Default(
    primary_hue="neutral",
    secondary_hue="neutral",
    neutral_hue="slate",
).set(
    body_background_fill="#f9fafb",
    block_background_fill="#ffffff",
    block_border_color="#e5e7eb",
    block_radius="8px",
    button_primary_background_fill="#111827",
    button_primary_background_fill_hover="#1f2937",
    button_primary_text_color="#ffffff",
)

CUSTOM_CSS = """
body { background-color: #f9fafb; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.gradio-container { max-width: 1400px !important; margin: auto; padding: 20px; }
h3, h4 { color: #111827 !important; font-weight: 700 !important; }
.gr-button-primary { background-color: #111827 !important; color: #ffffff !important; border-radius: 6px !important; font-weight: 600 !important; }
.gr-button-secondary { background-color: #f3f4f6 !important; color: #374151 !important; border: 1px solid #d1d5db !important; border-radius: 6px !important; }
.download-row .wrap { gap: 10px !important; align-items: center; }
.card-ecommerce { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
"""

with gr.Blocks(theme=THEME, css=CUSTOM_CSS, head=HEAD_JS, title="Liverpool Catalog Manager – Pro") as demo:
    df_state = gr.State()
    
    with gr.Row(elem_classes=["card-ecommerce"]):
        with gr.Column():
            gr.Markdown("## 🛍️ Liverpool Catalog & Assets Manager (Distribuido 10 Motores)")
            gr.Markdown("<p style='color: #6b7280; margin: 0; font-size: 13px;'>Panel de control optimizado para extracción masiva de productos e imágenes.</p>")

    with gr.Row():
        # COLUMNA IZQUIERDA: Controles
        with gr.Column(scale=1):
            with gr.Tabs():
                with gr.TabItem("📝 Carga Manual"):
                    skus_in = gr.Textbox(lines=5, label="Categoría + SKUs", placeholder="Zapatos\t12501544\t14152211")
                    btn_proc_paste = gr.Button("⚙️ Procesar Lote Manual", variant="primary", size="lg")
                    
                with gr.TabItem("🔍 Catálogo Web"):
                    cat_n1 = gr.Dropdown(label="Principal", choices=list(CATALOGO_LIVERPOOL.keys()), value="Mujer")
                    cat_n2 = gr.Dropdown(label="Subcategoría 1", choices=list(CATALOGO_LIVERPOOL["Mujer"].keys()))
                    cat_n3 = gr.Dropdown(label="Subcategoría 2", choices=list(CATALOGO_LIVERPOOL["Mujer"].get("Ropa", {}).keys()))
                    limit_destacados = gr.Number(label="Límite de productos", value=50, precision=0, minimum=1, maximum=200)
                    btn_proc_cat = gr.Button("🚀 Extraer Destacados", variant="primary", size="lg")

            with gr.Accordion("⚙️ Ajustes de Motores (Avanzado)", open=False):
                workers_input = gr.Textbox(label="URLs de los 10 Motores", value=DEFAULT_WORKERS, lines=3)
                with gr.Row():
                    delay_global = gr.Slider(0.0, 2.0, value=0.0, step=0.1, label="Delay (seg)")
                    google_global = gr.Checkbox(value=True, label="Google Search")
                with gr.Row():
                    show_url_global = gr.Checkbox(value=True, label="Ver URL")
                    show_name_global = gr.Checkbox(value=True, label="Ver Nombre")
                    show_strat_global = gr.Checkbox(value=False, label="Ver Estrategia")

            with gr.Column(elem_classes=["download-row"], visible=False) as export_panel:
                gr.Markdown("### 📥 Exportar Resultados")
                download_feed_shared = gr.DownloadButton("⬇️ Descargar Feed CSV", variant="primary", visible=False)
                btn_master_zip = gr.Button("📦 Generar ZIP de Imágenes", variant="secondary")
                download_master_zip = gr.DownloadButton("⬇️ Descargar ZIP Maestro", variant="primary", visible=False)

        # COLUMNA DERECHA: Resultados
        with gr.Column(scale=2):
            out_stats_shared = gr.HTML(visible=False) 
            out_duplicates_shared = gr.HTML(visible=False) 
            out_broken_md_shared = gr.HTML(visible=False) 

            gr.Markdown("### 🖼️ Galería en Tiempo Real")
            out_gallery_shared = gr.HTML(label="Galería")
            
            with gr.Accordion("📊 Tabla de Datos (Feed)", open=False):
                out_preview_shared = gr.Dataframe(interactive=False, wrap=True, label="Data Feed")

    notif_audio = gr.Audio(label="Notificación", autoplay=True, interactive=False, visible=False)

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

    def handler_paste(skus_text, workers_url, delay, use_g, s_url, s_name, s_strat):
        parsed, duplicates = parse_grouped_skus(skus_text)
        if not parsed: raise gr.Error("No se encontraron SKUs válidos.")
        for step in core_engine_distribuido(parsed, duplicates, workers_url, delay, use_g, s_url, s_name, s_strat, "MANUAL"):
            if len(step) == 7: yield (*step, gr.update(visible=True))
            else: yield step

    def handler_extract(n1, n2, n3, limit, workers_url, delay, use_g, s_url, s_name, s_strat):
        if not n1 or not n2 or not n3: raise gr.Error("Selecciona la jerarquía completa.")
        url = CATALOGO_LIVERPOOL.get(n1, {}).get(n2, {}).get(n3, "")
        if not url: raise gr.Error("URL no encontrada.")
        
        yield (gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(value=""), gr.update(value=pd.DataFrame()), gr.update(), gr.update(value=None, visible=False), gr.update(visible=False))
        
        skus = extraer_skus_de_categoria_maestro(url, limit=int(limit))
        if not skus: raise gr.Error("Categoría vacía.")
        
        parsed = [(f"{n1} - {n3}", sku) for sku in skus]
        for step in core_engine_distribuido(parsed, {}, workers_url, delay, use_g, s_url, s_name, s_strat, "DESTACADOS"):
            if len(step) == 7: yield (*step, gr.update(visible=True))
            else: yield step

    btn_proc_paste.click(
        fn=handler_paste,
        inputs=[skus_in, workers_input, delay_global, google_global, show_url_global, show_name_global, show_strat_global],
        outputs=[out_stats_shared, out_duplicates_shared, out_broken_md_shared, out_gallery_shared, out_preview_shared, df_state, notif_audio, download_feed_shared],
        show_progress="hidden"
    ).then(fn=lambda: gr.update(visible=True), outputs=[export_panel])

    btn_proc_cat.click(
        fn=handler_extract,
        inputs=[cat_n1, cat_n2, cat_n3, limit_destacados, workers_input, delay_global, google_global, show_url_global, show_name_global, show_strat_global],
        outputs=[out_stats_shared, out_duplicates_shared, out_broken_md_shared, out_gallery_shared, out_preview_shared, df_state, notif_audio, download_feed_shared],
        show_progress="hidden"
    ).then(fn=lambda: gr.update(visible=True), outputs=[export_panel])

    def pre_zip_ui(): return gr.update(value="⏳ Empacando...", interactive=False)
    def post_zip_ui(): return gr.update(value="📦 Generar ZIP de Imágenes", interactive=True)

    btn_master_zip.click(fn=pre_zip_ui, inputs=[], outputs=[btn_master_zip]).then(
        fn=generate_master_zip, inputs=[df_state], outputs=[download_master_zip]
    ).then(fn=post_zip_ui, inputs=[], outputs=[btn_master_zip])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)

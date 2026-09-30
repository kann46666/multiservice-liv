# app.py – V8.8 Maestro Estilo Liverpool (Cabecera Rosa + Contenido Blanco)
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
            "Vestidos": "https://www.liverpool.com.mx/tienda/vestidos/catst4003101",
        },
        "Zapatos": {
            "Tenis Casuales": "https://www.liverpool.com.mx/tienda/tenis-casuales/catst4003357",
            "Sandalias": "https://www.liverpool.com.mx/tienda/sandalias/catst4003354",
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

def extraer_skus_de_categoria_maestro(url: str, limit: int = 50) -> list[str]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "es-MX,es;q=0.9",
            "Referer": BASE_HOME,
        }
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200 or not r.text:
            return []
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
    except Exception:
        return []

def consultar_worker(worker_url: str, item_sku: tuple[str, str], usar_google: bool) -> dict:
    url = worker_url.strip().rstrip("/") + "/procesar_lote"
    payload = {"skus": [list(item_sku)], "usar_google": usar_google}
    for intento in range(2):
        try:
            resp = requests.post(url, json=payload, timeout=WORKER_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            time.sleep(1)
    grupo, sku = item_sku
    return {"valid_records": [], "offline": {grupo: [sku]}}

def core_engine_distribuido(parsed_skus, duplicates_dict, workers_str, delay_val, usar_google_val, show_url_val, show_name_val, show_strategy_val, prefix="ENTREGABLE"):
    total = len(parsed_skus)
    workers = [w.strip() for w in workers_str.split(",") if w.strip()]
    if not workers:
        raise gr.Error("Configura al menos una URL de Motor válida.")
    
    num_workers = len(workers)
    initial_spinner = generate_inline_spinner(0, 0, total, f"Conectando con {num_workers} motores en paralelo...")
    
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
                executor.submit(consultar_worker, workers[idx], item, usar_google_val)
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
                    if grupo not in offline_dict:
                        offline_dict[grupo] = []
                    for s in skus_list:
                        if s not in offline_dict[grupo]:
                            offline_dict[grupo].append(s)

            done += len(wave_items)
            if delay_val > 0:
                time.sleep(delay_val)

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
    feed_path = _write_csvs(final_df, f"{prefix}_V8_8")
    
    success_card = f"""
    <div style="background: linear-gradient(to right, #ecfdf5, #d1fae5); border-left: 6px solid #10b981; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0; color: #064e3b; font-size: 20px; font-weight: bold; display: flex; align-items: center; gap: 8px;">
            🎉 ¡Entregable Listo y Procesado Exitosamente ({num_workers} Motores)!
        </h3>
        <div style="display: flex; gap: 20px; font-size: 15px; flex-wrap: wrap;">
            <div style="color: #064e3b;"><strong style="color: #064e3b;">SKUs Validados:</strong> <span style="background: #a7f3d0; padding: 2px 8px; border-radius: 4px; color: #064e3b; font-weight: bold;">{len(valid_records)}</span></div>
            <div style="color: #064e3b;"><strong style="color: #064e3b;">Categorías Detectadas:</strong> <span style="background: #a7f3d0; padding: 2px 8px; border-radius: 4px; color: #064e3b; font-weight: bold;">{final_df['Grupo_Pegado'].nunique() if not final_df.empty else 0}</span></div>
            <div style="color: #064e3b;"><strong style="color: #064e3b;">Tiempo Total:</strong> <span style="background: #a7f3d0; padding: 2px 8px; border-radius: 4px; color: #064e3b; font-weight: bold;">{fmt_duration(time.monotonic() - t0)}</span></div>
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

def generate_master_zip(df, progress=gr.Progress()):
    if df is None or df.empty: raise gr.Error("No hay datos para generar el ZIP.")
    ts = int(time.time())
    zip_filename = f"IMAGENES_LIVERPOOL_V8_8_{ts}.zip"
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
    <div style="display: flex; align-items: center; justify-content: center; padding: 25px; margin-top: 15px; background: #fff; border: 2px dashed #e3007b; border-radius: 8px;">
        <div style="display: flex; flex-direction: column; align-items: center;">
            <div class="loader" style="border: 4px solid #fce4ec; border-top: 4px solid #e3007b; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite;"></div>
            <div style="margin-top: 12px; font-size: 15px; font-weight: 800; color: #334155;">Procesando con 10 Motores... {pct}%</div>
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
            
            prefix = f"<span style='color: #e3007b; background-color: #fce4ec; padding: 2px 8px; border-radius: 4px; margin-right: 8px;'>[{grupo_pegado}]</span>" if grupo_pegado != "General" else ""
            title = f"{prefix}{name} (SKU: {sku})" if name else f"{prefix}SKU: {sku}"
            
            valid_imgs = [row.get(c, "") for c in img_cols if str(row.get(c, "")).startswith("http")]
            if not valid_imgs: continue
            
            badge_text = f"Se encontraron {len(valid_imgs)} imágenes"
            urls_str = "|".join(valid_imgs)
            folder_name_safe = re.sub(r'[\\/*?:"<>|\']', "", f"{grupo_pegado + ' - ' if grupo_pegado != 'General' else ''}{name} - {sku}").replace('"', '').replace("'", "").strip()
            
            actions_html = f"""
            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
                {f'<a href="{url}" target="_blank" style="text-decoration: none; background-color: #fce4ec; color: #e3007b; padding: 6px 12px; border-radius: 9999px; font-size: 13px; font-weight: bold; border: 1px solid #f8bbd0;">🛒 Ver en tienda</a>' if url else ''}
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
                        <div style="display: flex; justify-content: space-between; font-size: 14px;"><span style="color: #4b5563; font-weight: 600;">Precio Actual:</span> <span style="color: #e3007b; font-size: 18px; font-weight: 800;">${p_act_val:,.2f}</span></div>
                        <div style="text-align: right; margin-top: 4px;"><span style="background-color: #fef2f2; color: #dc2626; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; border: 1px solid #fecaca;">-{pct} DESC.</span></div>
                    </div>"""
                else:
                    prices_html = f"""<div style="margin-top: auto; border-top: 1px solid #e5e7eb; padding-top: 12px; display: flex; justify-content: space-between; font-size: 14px;">
                        <span style="color: #4b5563; font-weight: 600;">Precio:</span> <span style="color: #1f2937; font-size: 18px; font-weight: 800;">${p_act_val:,.2f}</span>
                    </div>"""
                
            box_html = f"""<div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 8px; align-items: stretch;">
                <div style="flex: 3 1 500px; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; background-color: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <h4 style="margin: 0 0 16px 0; color: #1e293b; font-size: 16px; font-weight: bold;">📦 {title}</h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 12px;">"""
            for img in valid_imgs:
                box_html += f'<div style="width: 150px; height: 200px; border: 1px solid #f1f5f9; border-radius: 6px; overflow: hidden; display: flex; justify-content: center; align-items: center; background: #ffffff;"><img src="{img}" style="max-width: 100%; max-height: 100%; object-fit: contain;"/></div>'
            box_html += f"""</div></div>
                <div style="flex: 1 1 250px; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; background-color: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: space-between;">
                    <div>{actions_html}<span style="background-color: #fce4ec; color: #e3007b; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: bold; border: 1px solid #f8bbd0;">📸 {badge_text}</span>{metadata_html}</div>
                    {prices_html}
                </div></div>"""
            html_blocks.append(box_html)
            
    if spinner_html:
        html_blocks.append(spinner_html)
        
    html_blocks.append('</div>')
    return "\n".join(html_blocks)

def generate_duplicates_html(duplicates_dict: dict) -> str:
    if not duplicates_dict: return ""
    count = sum(len(skus) for skus in duplicates_dict.values())
    lines_html = ""
    for g, skus in duplicates_dict.items():
        g_name = g if str(g).strip() and str(g)!='General' else 'Sin Categoría'
        lines_html += f'<div style="color: #854d0e;"><strong>[{g_name}]:</strong> {", ".join(skus)}</div>'
    return f"""
    <div style="background: linear-gradient(to right, #fefce8, #fef9c3); border-left: 6px solid #eab308; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px;">
        <h3 style="margin: 0 0 8px 0; color: #854d0e; font-size: 18px; font-weight: bold;">⚠️️ PRODUCTOS REPETIDOS / Omitidos: {count}</h3>
        <p style="margin: 0 0 12px 0; color: #a16207; font-size: 14px;">Estos SKUs ya estaban en la lista y fueron omitidos:</p>
        <div style="display: flex; flex-direction: column; gap: 6px; font-size: 14px;">{lines_html}</div>
    </div>
    """

def generate_offline_html(offline_dict: dict) -> str:
    if not offline_dict: return ""
    count = sum(len(skus) for skus in offline_dict.values())
    lines_html = ""
    for g, skus in offline_dict.items():
        g_name = g if str(g).strip() and str(g)!='General' else 'Sin Categoría'
        lines_html += f'<div style="color: #7f1d1d;"><strong>[{g_name}]:</strong> {", ".join(skus)}</div>'
    return f"""
    <div style="background: linear-gradient(to right, #fef2f2, #fee2e2); border-left: 6px solid #ef4444; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px;">
        <h3 style="margin: 0 0 8px 0; color: #7f1d1d; font-size: 18px; font-weight: bold;">⚠️ PRODUCTOS OFF / Descatalogados: {count}</h3>
        <p style="margin: 0 0 12px 0; color: #991b1b; font-size: 14px;">Estos SKUs no arrojaron resultados y NO se agregaron al CSV:</p>
        <div style="display: flex; flex-direction: column; gap: 6px; font-size: 14px;">{lines_html}</div>
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
    if (typeof window.JSZip === 'undefined') { alert("Librerías cargando, intenta en un segundo."); return; }
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
            try { let resp = await fetch(url); if (!resp.ok) throw new Error(); blob = await resp.blob(); }
            catch(err) { try { let resp = await fetch('https://corsproxy.io/?' + encodeURIComponent(url)); if (resp.ok) blob = await resp.blob(); } catch(err2) { } }
            if (blob) { let ext = url.split('.').pop().split('?')[0]; folder.file("imagen_" + (i+1) + "." + (ext.length > 4 || !ext ? 'jpg' : ext), blob); downloaded++; }
        }
        if (downloaded === 0 && urls.length > 0) alert("No se pudo descargar por bloqueos del navegador. Usa el botón superior de ZIP Maestro.");
        else {
            const content = await zip.generateAsync({type:"blob"});
            const link = document.createElement('a'); link.href = URL.createObjectURL(content);
            link.download = folderName + ".zip"; document.body.appendChild(link); link.click();
            document.body.removeChild(link); setTimeout(() => URL.revokeObjectURL(link.href), 2000);
        }
    } catch(err) { alert("Error al crear el ZIP."); }
    btn.innerHTML = originalText; btn.style.pointerEvents = "auto"; btn.style.opacity = "1";
});
</script>
"""

# ============================ CSS Estilo Liverpool ============================
CUSTOM_CSS = """
/* Fondo general de la aplicación en blanco puro */
body, .gradio-container {
    background-color: #ffffff !important;
}

/* Cabecera superior y sección de pestañas y botones con el rosa institucional de Liverpool */
.liverpool-header-box {
    background-color: #e3007b !important;
    padding: 20px !important;
    border-radius: 12px !important;
    color: white !important;
    margin-bottom: 20px !important;
}

.liverpool-header-box h3, .liverpool-header-box label, .liverpool-header-box span, .liverpool-header-box p {
    color: white !important;
}

/* Botones principales con acento rosa brillante y letras blancas */
button.primary {
    background-color: #e3007b !important;
    border-color: #e3007b !important;
    color: white !important;
    font-weight: bold !important;
}

button.primary:hover {
    background-color: #c5006b !important;
}

.download-row .wrap { gap: 8px !important; align-items: center; }
"""

# ============================ Interfaz de Usuario ============================

try: THEME = gr.themes.Soft(primary_hue="pink", secondary_hue="rose", neutral_hue="slate")
except: THEME = gr.themes.Soft()

with gr.Blocks(title="Liverpool – Generador Distribuido") as demo:
    df_state = gr.State()
    
    # Contenedor superior con estilo Liverpool (Rosa)
    with gr.Column(elem_classes=["liverpool-header-box"]):
        gr.Markdown("## 🛍️ Liverpool – Sistema Maestro Distribuido (10 Motores)")
        gr.Markdown("Herramienta de extracción masiva con identidad visual oficial.")

        with gr.Tabs():
            with gr.TabItem("📝 Pegar SKUs / Excel"):
                skus_in = gr.Textbox(lines=5, label="Pega tu tabla (Categoría + SKUs mezclados)", placeholder="Zapatos\t12501544\t14152211")
                btn_proc_paste = gr.Button("⚙️ Procesar Tabla Manual (10 Motores)", variant="primary")
                
            with gr.TabItem("🔍 Extraer Destacados (Automático)"):
                gr.Markdown("Selecciona la categoría para extraer los productos destacados directamente de la tienda.")
                with gr.Row():
                    cat_n1 = gr.Dropdown(label="Categoría Principal", choices=list(CATALOGO_LIVERPOOL.keys()), value="Mujer")
                    cat_n2 = gr.Dropdown(label="Subcategoría 1", choices=list(CATALOGO_LIVERPOOL["Mujer"].keys()))
                    cat_n3 = gr.Dropdown(label="Subcategoría 2", choices=list(CATALOGO_LIVERPOOL["Mujer"].get("Ropa", {}).keys()))
                
                limit_destacados = gr.Number(label="Cantidad máxima a extraer", value=50, precision=0, minimum=1, maximum=200)
                btn_proc_cat = gr.Button("🚀 Extraer y Procesar Destacados (10 Motores)", variant="primary")

        with gr.Accordion("⚙️ Ajustes de Procesamiento (Avanzado)", open=False):
            workers_input = gr.Textbox(
                label="URLs de los 10 Motores (separadas por coma)", 
                value=DEFAULT_WORKERS,
                lines=2
            )
            with gr.Row():
                delay_global = gr.Slider(0.0, 2.0, value=0.0, step=0.1, label="Delay entre oleadas de 10 (seg)")
                google_global = gr.Checkbox(value=True, label="Usar Google (más preciso)")
            with gr.Row():
                show_url_global = gr.Checkbox(value=True, label="Mostrar producto_url (vista previa)")
                show_name_global = gr.Checkbox(value=True, label="Mostrar Producto_Nombre (vista previa)")
                show_strat_global = gr.Checkbox(value=False, label="Mostrar Estrategia (vista previa)")

    gr.Markdown("---")
    
    out_stats_shared = gr.HTML(visible=False) 
    out_duplicates_shared = gr.HTML(visible=False) 
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

    def handler_paste(skus_text, workers_url, delay, use_g, s_url, s_name, s_strat):
        parsed, duplicates = parse_grouped_skus(skus_text)
        if not parsed: raise gr.Error("No se encontraron SKUs válidos.")
        for step in core_engine_distribuido(parsed, duplicates, workers_url, delay, use_g, s_url, s_name, s_strat, "MANUAL"):
            if len(step) == 7:
                yield (*step, gr.update(visible=False))
            else:
                yield step

    def handler_extract(n1, n2, n3, limit, workers_url, delay, use_g, s_url, s_name, s_strat):
        if not n1 or not n2 or not n3: raise gr.Error("Selecciona la jerarquía completa de categorías.")
        url = CATALOGO_LIVERPOOL.get(n1, {}).get(n2, {}).get(n3, "")
        if not url: raise gr.Error("No se encontró la URL en el catálogo.")
        
        yield (gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(value=""), gr.update(value=pd.DataFrame()), gr.update(), gr.update(value=None, visible=False), gr.update(visible=False))
        
        skus = extraer_skus_de_categoria_maestro(url, limit=int(limit))
        if not skus: raise gr.Error("No se lograron extraer productos. La categoría podría estar vacía.")
        
        grupo_nombre = f"{n1} - {n3}"
        parsed = [(grupo_nombre, sku) for sku in skus]
        for step in core_engine_distribuido(parsed, {}, workers_url, delay, use_g, s_url, s_name, s_strat, "DESTACADOS"):
            if len(step) == 7:
                yield (*step, gr.update(visible=False))
            else:
                yield step

    btn_proc_paste.click(
        fn=handler_paste,
        inputs=[skus_in, workers_input, delay_global, google_global, show_url_global, show_name_global, show_strat_global],
        outputs=[out_stats_shared, out_duplicates_shared, out_broken_md_shared, out_gallery_shared, out_preview_shared, df_state, notif_audio, download_feed_shared],
        show_progress="hidden"
    ).then(
        fn=lambda: gr.update(visible=True), 
        outputs=[btn_master_zip]
    )

    btn_proc_cat.click(
        fn=handler_extract,
        inputs=[cat_n1, cat_n2, cat_n3, limit_destacados, workers_input, delay_global, google_global, show_url_global, show_name_global, show_strat_global],
        outputs=[out_stats_shared, out_duplicates_shared, out_broken_md_shared, out_gallery_shared, out_preview_shared, df_state, notif_audio, download_feed_shared],
        show_progress="hidden"
    ).then(
        fn=lambda: gr.update(visible=True), 
        outputs=[btn_master_zip]
    )

    def pre_zip_ui(): return gr.update(value="⏳ ✨ Empacando imágenes...", interactive=False)
    def post_zip_ui(): return gr.update(value="📦 Generar ZIP de Imágenes", interactive=True)

    btn_master_zip.click(fn=pre_zip_ui, inputs=[], outputs=[btn_master_zip]).then(
        fn=generate_master_zip, inputs=[df_state], outputs=[download_master_zip]
    ).then(fn=post_zip_ui, inputs=[], outputs=[btn_master_zip])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(
        server_name="0.0.0.0", 
        server_port=port, 
        theme=THEME, 
        css=CUSTOM_CSS, 
        head=HEAD_JS
    )

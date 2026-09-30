# app.py – V8.7 Maestro Distribuido (Round-Robin)
import os
import re
import time
import json
import zipfile
import typing as t
import concurrent.futures

import pandas as pd
import gradio as gr
import requests

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

DEFAULT_TIMEOUT = 30
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

# ====================== Distribuidor a Workers (Round-Robin) ======================

def consultar_worker(worker_url: str, chunk_skus: list[tuple[str, str]], usar_google: bool) -> dict:
    """Envía un lote de SKUs asignados a un Motor específico vía POST"""
    try:
        url = worker_url.strip().rstrip("/") + "/procesar_lote"
        payload = {"skus": chunk_skus, "usar_google": usar_google}
        resp = requests.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error comunicándose con el worker {worker_url}: {e}")
    return {"valid_records": [], "offline": {}}

def procesar_distribuido(parsed_skus, workers_str, usar_google_val, delay_val, show_url_val, show_name_val, show_strategy_val, prefix="ENTREGABLE"):
    total = len(parsed_skus)
    initial_spinner = generate_inline_spinner(0, 0, total, "Iniciando motores distribuidos...")
    
    yield (
        gr.update(), gr.update(), gr.update(), 
        gr.update(value=build_html_gallery(pd.DataFrame(), spinner_html=initial_spinner)), 
        gr.update(value=pd.DataFrame()), gr.update(), gr.update(value=None, visible=False)
    )

    workers = [w.strip() for w in workers_str.split(",") if w.strip()]
    if not workers:
        workers = ["http://localhost:7860"]

    # DISTRIBUCIÓN ROUND-ROBIN: Repartir de uno en uno por cada motor
    worker_buckets = [[] for _ in range(len(workers))]
    for idx, item in enumerate(parsed_skus):
        target_worker_idx = idx % len(workers)
        worker_buckets[target_worker_idx].append(item)

    valid_records = []
    offline_dict = {}
    t0 = time.monotonic()

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(workers)) as executor:
        future_to_worker = {
            executor.submit(consultar_worker, workers[i], worker_buckets[i], usar_google_val): i 
            for i in range(len(workers)) if worker_buckets[i]
        }

        done_count = 0
        all_results_map = {}

        for future in concurrent.futures.as_completed(future_to_worker):
            res = future.result()
            batch_valid = res.get("valid_records", [])
            batch_offline = res.get("offline", {})

            for rec in batch_valid:
                all_results_map[rec["Producto"]] = rec
                done_count += 1

            for grupo, skus_list in batch_offline.items():
                if grupo not in offline_dict: offline_dict[grupo] = []
                for s in skus_list:
                    if s not in offline_dict[grupo]: offline_dict[grupo].append(s)

        # Reconstruir la lista final respetando estrictamente el orden original
        ordered_valid_records = []
        for _, sku in parsed_skus:
            if sku in all_results_map:
                ordered_valid_records.append(all_results_map[sku])

        for i, rec in enumerate(ordered_valid_records):
            rec["ID"] = i + 1

        elapsed = max(1e-6, time.monotonic() - t0)
        temp_df = pd.DataFrame(ordered_valid_records)
        current_spinner = generate_inline_spinner(100, total, total, fmt_duration(elapsed))
        temp_gallery = build_html_gallery(temp_df, spinner_html="")
        temp_preview = _preview_with_toggles(temp_df, show_url_val, show_name_val, show_strategy_val) if not temp_df.empty else pd.DataFrame()

        yield (
            gr.update(), gr.update(), gr.update(), 
            gr.update(value=temp_gallery), 
            gr.update(value=temp_preview), 
            temp_df, 
            gr.update(value=None, visible=False)
        )

    final_df = pd.DataFrame(ordered_valid_records)
    _write_csvs(final_df, f"{prefix}_V8_7")
    
    success_card = f"""
    <div style="background: linear-gradient(to right, #ecfdf5, #d1fae5); border-left: 6px solid #10b981; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px;">
        <h3 style="margin: 0 0 10px 0; color: #064e3b; font-size: 20px; font-weight: bold; display: flex; align-items: center; gap: 8px;">
            🎉 ¡Procesamiento Distribuido Round-Robin Exitoso!
        </h3>
        <div style="display: flex; gap: 20px; font-size: 15px;">
            <div style="color: #064e3b;"><strong style="color: #064e3b;">SKUs Validados:</strong> <span style="background: #a7f3d0; padding: 2px 8px; border-radius: 4px; color: #064e3b; font-weight: bold;">{len(ordered_valid_records)}</span></div>
            <div style="color: #064e3b;"><strong style="color: #064e3b;">Motores Activos:</strong> <span style="background: #a7f3d0; padding: 2px 8px; border-radius: 4px; color: #064e3b; font-weight: bold;">{len(workers)}</span></div>
        </div>
    </div>
    """
    
    yield (
        gr.update(value=success_card, visible=True),
        gr.update(value="", visible=False),
        gr.update(value=generate_offline_html(offline_dict), visible=True),
        gr.update(value=build_html_gallery(final_df, spinner_html="")), 
        gr.update(value=_preview_with_toggles(final_df, show_url_val, show_name_val, show_strategy_val)),
        final_df, 
        gr.update(value=NOTIFY_SOUND, visible=True)
    )

# ====================== UI Helpers & Componentes Visuales ======================
def generate_master_zip(df, progress=gr.Progress()):
    if df is None or df.empty: raise gr.Error("No hay datos para generar el ZIP.")
    ts = int(time.time())
    zip_filename = f"IMAGENES_LIVERPOOL_DISTRIB_{ts}.zip"
    session = requests.Session()
    total_rows = len(df)
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for idx, row in df.iterrows():
            progress((idx + 1) / total_rows, desc=f"Descargando producto {idx+1}/{total_rows}")
            grupo = _coerce_nonempty_str(row.get("Grupo_Pegado", "General"))
            nombre = _coerce_nonempty_str(row.get("Producto_Nombre", "Producto"))
            sku = _coerce_nonempty_str(row.get("Producto", "SKU"))
            folder_name = f"{re.sub(r'[\\/*?:\"<>|]', '', grupo)}/{re.sub(r'[\\/*?:\"<>|]', '', nombre)} - {sku}"
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
    <div style="display: flex; align-items: center; justify-content: center; padding: 25px; margin-top: 15px; background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 8px;">
        <div style="display: flex; flex-direction: column; align-items: center;">
            <div class="loader" style="border: 4px solid #e2e8f0; border-top: 4px solid #3b82f6; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite;"></div>
            <div style="margin-top: 12px; font-size: 15px; font-weight: 800; color: #334155;">Procesando Distribuido Round-Robin... {pct}%</div>
            <div style="font-size: 12px; font-weight: 600; color: #64748b; margin-top: 4px;">Procesados {done} de {total} productos en paralelo</div>
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
            grupo_pegado = _coerce_nonempty_str(row.get(cols.get("grupo_pegado"), "General"))
            valid_imgs = [row.get(c, "") for c in img_cols if str(row.get(c, "")).startswith("http")]
            if not valid_imgs: continue
            
            box_html = f"""<div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 8px; align-items: stretch;">
                <div style="flex: 3 1 500px; border: 1px solid #d1d5db; border-radius: 8px; padding: 16px; background-color: #f8fafc;">
                    <h4 style="margin: 0 0 16px 0; color: #4c1d95; font-size: 16px;">📦 [{grupo_pegado}] {name} (SKU: {sku})</h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 12px;">"""
            for img in valid_imgs:
                box_html += f'<div style="width: 130px; height: 170px; border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden; display: flex; justify-content: center; align-items: center; background: #fff;"><img src="{img}" style="max-width: 100%; max-height: 100%; object-fit: contain;"/></div>'
            box_html += "</div></div></div>"
            html_blocks.append(box_html)
    if spinner_html: html_blocks.append(spinner_html)
    html_blocks.append('</div>')
    return "\n".join(html_blocks)

def generate_offline_html(offline_dict: dict) -> str:
    if not offline_dict: return ""
    count = sum(len(skus) for skus in offline_dict.values())
    return f"""<div style="background: #fef2f2; border-left: 6px solid #ef4444; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
        <h3 style="margin: 0; color: #7f1d1d; font-size: 16px;">⚠️ Productos Off / Descatalogados: {count}</h3></div>"""

def _preview_with_toggles(full_df, show_url, show_name, show_strategy):
    cols = ["ID", "Grupo_Pegado", "Producto", "Categoria", "Marca", "Estado", "Precio_Actual", "Precio_Original", "Descuento_Porcentaje"]
    return full_df.loc[:, [c for c in cols if c in full_df.columns]]

def _write_csvs(full_df, prefix):
    fp = f"{prefix}_FEED_{int(time.time())}.csv"
    full_df.to_csv(fp, index=False, encoding="utf-8")
    return fp

HEAD_JS = "<script src='https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js'></script>"

# ====================== Interfaz Gradio Maestro ======================
try: THEME = gr.themes.Soft(primary_hue="fuchsia", secondary_hue="violet", neutral_hue="slate")
except: THEME = gr.themes.Soft()
CUSTOM_CSS = ".download-row .wrap { gap: 8px !important; align-items: center; }"

with gr.Blocks(title="Maestro Distribuido Liverpool") as demo:
    df_state = gr.State()
    gr.Markdown("### 🧠 V8.7 – Cerebro Maestro (Procesamiento Distribuido Round-Robin)")

    with gr.Tabs():
        with gr.TabItem("📝 Pegar SKUs"):
            skus_in = gr.Textbox(lines=5, label="Pega tu tabla (Categoría + SKUs)", placeholder="Zapatos\t12501544")
            btn_proc_paste = gr.Button("⚙️ Procesar Distribuido", variant="primary")

    with gr.Accordion("⚙️ Configuración de Motores (Workers)", open=True):
        workers_input = gr.Textbox(
            label="URLs de Motores (separadas por coma)", 
            value="https://tu-motor-1.onrender.com, https://tu-motor-2.onrender.com",
            placeholder="https://motor1.onrender.com, https://motor2.onrender.com"
        )
        with gr.Row():
            delay_global = gr.Slider(0.0, 2.0, value=0.1, step=0.1, label="Delay interno")
            google_global = gr.Checkbox(value=True, label="Usar Google")
        with gr.Row():
            show_url_global = gr.Checkbox(value=True, label="Mostrar URL")
            show_name_global = gr.Checkbox(value=True, label="Mostrar Nombre")
            show_strat_global = gr.Checkbox(value=False, label="Mostrar Estrategia")

    out_stats_shared = gr.HTML(visible=False)
    out_duplicates_shared = gr.HTML(visible=False)
    out_broken_md_shared = gr.HTML(visible=False)

    with gr.Row():
        download_feed_shared = gr.DownloadButton("⬇️ DESCARGAR CSV", visible=False, variant="primary")
        btn_master_zip = gr.Button("📦 Generar ZIP", visible=False, variant="secondary")
        download_master_zip = gr.DownloadButton("⬇️ DESCARGAR ZIP", visible=False, variant="primary")

    out_gallery_shared = gr.HTML(label="Preview")
    out_preview_shared = gr.Dataframe(interactive=False)
    notif_audio = gr.Audio(autoplay=True, visible=False)

    def handler_paste(skus_text, workers_url, delay, use_g, s_url, s_name, s_strat):
        parsed, duplicates = parse_grouped_skus(skus_text)
        if not parsed: raise gr.Error("No se encontraron SKUs válidos.")
        yield from procesar_distribuido(parsed, workers_url, use_g, delay, s_url, s_name, s_strat, "MANUAL")

    btn_proc_paste.click(
        fn=handler_paste,
        inputs=[skus_in, workers_input, delay_global, google_global, show_url_global, show_name_global, show_strat_global],
        outputs=[out_stats_shared, out_duplicates_shared, out_broken_md_shared, out_gallery_shared, out_preview_shared, df_state, notif_audio],
        show_progress="hidden"
    ).then(fn=lambda: (gr.update(visible=True), gr.update(visible=True)), outputs=[download_feed_shared, btn_master_zip])

    btn_master_zip.click(fn=lambda: gr.update(value="⏳ Empacando..."), outputs=[btn_master_zip]).then(
        fn=generate_master_zip, inputs=[df_state], outputs=[download_master_zip]
    ).then(fn=lambda: gr.update(value="📦 Generar ZIP"), outputs=[btn_master_zip])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(
        server_name="0.0.0.0", 
        server_port=port, 
        theme=THEME, 
        css=CUSTOM_CSS, 
        head=HEAD_JS
    )

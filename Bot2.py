import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import time
import threading
import random
from collections import deque
from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN PRINCIPAL ---
TOKEN_TELEGRAM = 'TU TOKEN DE TELEGRAM'
PASSWORD_SISTEMA = "1234"
MODO_OCULTO = False

# ⚠️ OBLIGATORIO: Pon tu ID numérico de Telegram (búscalo en @userinfobot)
ADMIN_CHAT_ID = "TU ID" 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_VIDEOS = os.path.join(BASE_DIR, 'cola_videos')
PERFIL_DIR = os.path.join(BASE_DIR, "tiktok_perfil_bot")

browser_lock = threading.Lock()
cola_normal = deque()

# Estado global para la moderación
estado_aprobacion = {"estado": "LIBRE"} 

if not os.path.exists(CARPETA_VIDEOS):
    os.makedirs(CARPETA_VIDEOS)

bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=True)

# --- SISTEMA DE AUTO-RECUPERACIÓN ---
def recuperar_cola_perdida():
    archivos = [f for f in os.listdir(CARPETA_VIDEOS) if f.endswith('.mp4')]
    archivos.sort(key=lambda x: os.path.getmtime(os.path.join(CARPETA_VIDEOS, x)))
    for archivo in archivos:
        ruta = os.path.join(CARPETA_VIDEOS, archivo)
        if ruta not in cola_normal:
            cola_normal.append(ruta)
    if cola_normal:
        print(f"[LOG] ♻️ Recuperados {len(cola_normal)} vídeos pendientes.")

# --- MODERACIÓN DE TELEGRAM ---
def pedir_aprobacion_admin(video_path):
    estado_aprobacion["estado"] = "PENDIENTE"
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("✅ Aceptar", callback_data="aceptar"),
        InlineKeyboardButton("❌ Rechazar", callback_data="rechazar")
    )
    
    try:
        with open(video_path, 'rb') as video:
            bot.send_video(
                ADMIN_CHAT_ID, 
                video, 
                caption=f"🛡️ **FILTRO DE MODERACIÓN**\n\nEste vídeo toca subirse en 1 HORA.\nArchivo: `{os.path.basename(video_path)}`\n\n¿Lo publicamos?", 
                reply_markup=markup,
                parse_mode="Markdown"
            )
    except Exception as e:
        print(f"[!] Error contactando al Admin: {e}. ¿Iniciaste el chat con el bot?")
        estado_aprobacion["estado"] = "ERROR"

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if estado_aprobacion["estado"] != "PENDIENTE":
        bot.answer_callback_query(call.id, "Esta solicitud ya fue procesada.")
        return
        
    if call.data == "aceptar":
        estado_aprobacion["estado"] = "ACEPTADO"
        bot.edit_message_caption(caption="✅ **ACEPTADO**.\nEl vídeo está en cola de publicación. Saldrá en 1 hora.", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
    elif call.data == "rechazar":
        estado_aprobacion["estado"] = "RECHAZADO"
        bot.edit_message_caption(caption="❌ **RECHAZADO**.\nBuscando el siguiente vídeo en la cola...", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")

# --- MOTOR DE SUBIDA (VERIFICACIÓN REAL) ---
def subir_a_tiktok(video_path, es_premium=False):
    tipo = "PREMIUM" if es_premium else "NORMAL"
    
    if not os.path.exists(video_path):
        return

    with browser_lock:
        print(f"\n[LOG] [{tipo}] Iniciando subida: {os.path.basename(video_path)}")
        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=PERFIL_DIR,
                    headless=MODO_OCULTO,
                    channel="chrome",
                    args=["--disable-blink-features=AutomationControlled"]
                )
                
                page = context.new_page()
                page.goto("https://www.tiktok.com/creator-center/upload?lang=es", timeout=60000)
                page.wait_for_timeout(5000)
                
                if "login" in page.url:
                    print(f"[LOG] ❌ [{tipo}] ERROR CRÍTICO: Sesión cerrada.")
                    if not es_premium: cola_normal.appendleft(video_path)
                    return

                page.locator("input[type='file']").set_input_files(video_path)
                
                boton_publicar = page.locator('button:has-text("Publicar"), button:has-text("Post")').first
                boton_publicar.wait_for(state="visible", timeout=30000)
                
                for _ in range(300):
                    if not boton_publicar.is_disabled():
                        break
                    time.sleep(1)
                
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)
                
                boton_publicar.click(force=True)
                boton_publicar.wait_for(state="hidden", timeout=120000)
                print(f"[LOG] ✅ [{tipo}] ÉXITO: Vídeo publicado.")
                page.wait_for_timeout(4000)

                if os.path.exists(video_path):
                    os.remove(video_path)

        except Exception as e:
            print(f"[LOG] ❌ [{tipo}] FALLO TÉCNICO: {e}")
            if not es_premium:
                cola_normal.appendleft(video_path)

# --- LÓGICA DE TIEMPOS (EMBUDO DE MODERACIÓN) ---
def hilo_programador_normal():
    while True:
        # Calcular el tiempo total y restar 1 hora (3600 segundos) para la moderación
        segundos_totales = random.randint(18000, 25200)
        tiempo_previo = segundos_totales - 3600
        
        print(f"\n[LOG] 🕒 Ciclo iniciado. Subida en {segundos_totales/3600:.2f}h. Te pediré permiso en {tiempo_previo/3600:.2f}h.")
        time.sleep(tiempo_previo)
        
        video_aprobado = None
        
        # Bucle de filtrado
        while cola_normal:
            video_candidato = cola_normal.popleft()
            print(f"[LOG] 🛡️ Enviando {os.path.basename(video_candidato)} a revisión...")
            
            pedir_aprobacion_admin(video_candidato)
            
            # Esperar a que pulses el botón en Telegram
            while estado_aprobacion["estado"] == "PENDIENTE":
                time.sleep(2)
                
            if estado_aprobacion["estado"] == "ACEPTADO":
                video_aprobado = video_candidato
                estado_aprobacion["estado"] = "LIBRE"
                break # Salimos del bucle de filtrado
                
            elif estado_aprobacion["estado"] == "RECHAZADO":
                if os.path.exists(video_candidato):
                    os.remove(video_candidato)
                print("[LOG] 🗑️ Vídeo rechazado por el Admin y eliminado físicamente.")
                estado_aprobacion["estado"] = "LIBRE"
                # El bucle while continúa y saca el siguiente vídeo de la cola instantáneamente
            
            elif estado_aprobacion["estado"] == "ERROR":
                # Si falla el envío a Telegram, devolvemos el vídeo y abortamos el ciclo
                cola_normal.appendleft(video_candidato)
                estado_aprobacion["estado"] = "LIBRE"
                break

        if video_aprobado:
            print("[LOG] ✅ Vídeo bloqueado y listo. Esperando la última hora (3600s) para publicar...")
            time.sleep(3600)
            subir_a_tiktok(video_aprobado, es_premium=False)
        else:
            print("[LOG] 🚫 No hay más vídeos en cola o rechazaste todos. Saltando este ciclo.")
            # Esperamos la hora restante para mantener el ciclo realista y no spamear
            time.sleep(3600)

def hilo_premium_rapido(video_path):
    print(f"[LOG] ⭐ Usuario Premium. Subiendo en 60s sin moderación...")
    time.sleep(60)
    subir_a_tiktok(video_path, es_premium=True)

# --- RECEPTOR DE TELEGRAM ---
@bot.message_handler(content_types=['video', 'document'])
def recibir_video(message):
    try:
        file_id = message.video.file_id if message.video else message.document.file_id
        file_info = bot.get_file(file_id)
        descargado = bot.download_file(file_info.file_path)
        
        ruta = os.path.join(CARPETA_VIDEOS, f"vid_{int(time.time())}.mp4")
        with open(ruta, 'wb') as f:
            f.write(descargado)
        
        caption = message.caption if message.caption else ""
        
        if f"/prem {PASSWORD_SISTEMA}" in caption:
            bot.reply_to(message, "⭐ **ACCESO PREMIUM**. Saltando filtro de moderación. Subida en 1 minuto.")
            threading.Thread(target=hilo_premium_rapido, args=(ruta,), daemon=True).start()
        else:
            cola_normal.append(ruta)
            bot.reply_to(message, f"✅ Recibido. Estás en la posición {len(cola_normal)} de la cola.")
            
    except Exception as e:
        print(f"Error procesando: {e}")

# --- INICIO ---
if __name__ == "__main__":
    print("=============================================")
    print("   🚀 BOT TIKTOK: PRODUCCIÓN BLINDADA")
    print("=============================================")
    if ADMIN_CHAT_ID == "PON_TU_ID_NUMERICO_AQUI":
        print("⚠️ ALERTA: No has configurado tu ADMIN_CHAT_ID. La moderación fallará.")
        
    recuperar_cola_perdida()
    threading.Thread(target=hilo_programador_normal, daemon=True).start()
    
    print("[LOG] Bot a la escucha...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            time.sleep(5)

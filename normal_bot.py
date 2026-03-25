import telebot
import os
import time
import threading
import random
from collections import deque
from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN PRINCIPAL ---
TOKEN_TELEGRAM = 'TU_TOKEN_AQUI' # ⚠️ Recuerda usar uno nuevo por seguridad
PASSWORD_SISTEMA = "1234"
MODO_OCULTO = False  # Cambia a True si no quieres ver cómo se abre el navegador

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_VIDEOS = os.path.join(BASE_DIR, 'cola_videos')
PERFIL_DIR = os.path.join(BASE_DIR, "tiktok_perfil_bot")

browser_lock = threading.Lock()
cola_normal = deque()

if not os.path.exists(CARPETA_VIDEOS):
    os.makedirs(CARPETA_VIDEOS)

bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=True)

# --- SISTEMA DE AUTO-RECUPERACIÓN ---
def recuperar_cola_perdida():
    """Lee la carpeta y mete en cola los vídeos que se quedaron sin subir si el bot se reinicia."""
    archivos = [f for f in os.listdir(CARPETA_VIDEOS) if f.endswith('.mp4')]
    # Ordenar por fecha de creación (el más viejo primero)
    archivos.sort(key=lambda x: os.path.getmtime(os.path.join(CARPETA_VIDEOS, x)))
    
    for archivo in archivos:
        ruta = os.path.join(CARPETA_VIDEOS, archivo)
        if ruta not in cola_normal:
            cola_normal.append(ruta)
    
    if cola_normal:
        print(f"[LOG] ♻️ Recuperados {len(cola_normal)} vídeos pendientes tras el reinicio.")

# --- MOTOR DE SUBIDA (VERIFICACIÓN REAL) ---
def subir_a_tiktok(video_path, es_premium=False):
    tipo = "PREMIUM" if es_premium else "NORMAL"
    
    if not os.path.exists(video_path):
        print(f"[LOG] ❌ ERROR: El archivo {video_path} ya no existe.")
        return

    with browser_lock:
        print(f"\n[LOG] [{tipo}] Iniciando subida para: {os.path.basename(video_path)}")
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
                
                # Seguridad: Si pide login en modo automático, abortamos y salvamos el vídeo
                if "login" in page.url:
                    print(f"[LOG] ❌ [{tipo}] ERROR CRÍTICO: TikTok ha cerrado la sesión.")
                    print("Por favor, ejecuta el script de prueba Light manualmente para volver a loguearte.")
                    if not es_premium: cola_normal.appendleft(video_path)
                    return

                print(f"[LOG] [{tipo}] Inyectando archivo...")
                page.locator("input[type='file']").set_input_files(video_path)
                
                boton_publicar = page.locator('button:has-text("Publicar"), button:has-text("Post")').first
                boton_publicar.wait_for(state="visible", timeout=30000)
                
                print(f"[LOG] [{tipo}] Esperando que el servidor procese el vídeo al 100%...")
                for _ in range(300):
                    if not boton_publicar.is_disabled():
                        break
                    time.sleep(1)
                
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)
                
                print(f"[LOG] [{tipo}] Clic en Publicar enviado. Verificando...")
                boton_publicar.click(force=True)
                
                # Verificación de éxito real
                boton_publicar.wait_for(state="hidden", timeout=120000)
                print(f"[LOG] ✅ [{tipo}] ÉXITO: Pantalla de subida superada. Vídeo publicado.")
                page.wait_for_timeout(4000)

                # Borrado de limpieza tras subida exitosa
                if os.path.exists(video_path):
                    os.remove(video_path)

        except Exception as e:
            print(f"[LOG] ❌ [{tipo}] FALLO TÉCNICO: {e}")
            # Si falla, se devuelve al principio de la cola para no perder el turno
            if not es_premium:
                cola_normal.appendleft(video_path)

# --- LÓGICA DE TIEMPOS (INTERVALOS ALEATORIOS) ---
def hilo_programador_normal():
    while True:
        # Entre 5 y 7 horas (18000 y 25200 segundos)
        segundos_espera = random.randint(18000, 25200)
        horas = round(segundos_espera / 3600, 2)
        print(f"\n[LOG] 🕒 Próximo vídeo normal programado en {horas} horas.")
        
        time.sleep(segundos_espera)
        
        if cola_normal:
            video = cola_normal.popleft()
            subir_a_tiktok(video, es_premium=False)
        else:
            print("[LOG] Cola normal vacía. Se reinicia el ciclo.")

def hilo_premium_rapido(video_path):
    print(f"[LOG] ⭐ Usuario Premium detectado. Subida forzada en 60 segundos...")
    time.sleep(60)
    subir_a_tiktok(video_path, es_premium=True)

# --- MANEJADORES DE TELEGRAM ---
@bot.message_handler(content_types=['video', 'document'])
def recibir_video(message):
    try:
        file_id = message.video.file_id if message.video else message.document.file_id
        file_info = bot.get_file(file_id)
        descargado = bot.download_file(file_info.file_path)
        
        # Guardamos con timestamp para mantener el orden
        ruta = os.path.join(CARPETA_VIDEOS, f"vid_{int(time.time())}.mp4")
        with open(ruta, 'wb') as f:
            f.write(descargado)
        
        caption = message.caption if message.caption else ""
        
        # Evaluar prioridad
        if f"/prem {PASSWORD_SISTEMA}" in caption:
            bot.reply_to(message, "⭐ **ACCESO PREMIUM**. Tu vídeo se publicará en aproximadamente 1 minuto.")
            threading.Thread(target=hilo_premium_rapido, args=(ruta,), daemon=True).start()
        else:
            cola_normal.append(ruta)
            bot.reply_to(message, f"✅ Vídeo guardado correctamente.\n📊 Posición en la cola: {len(cola_normal)}\n⏱️ Tiempo estimado: Se publicará por orden de llegada (1 vídeo cada 5-7h).")
            
    except Exception as e:
        print(f"Error procesando vídeo de Telegram: {e}")
        bot.reply_to(message, "Hubo un fallo al descargar tu vídeo. Inténtalo de nuevo.")

# --- INICIO DEL SISTEMA ---
if __name__ == "__main__":
    print("=============================================")
    print("   🚀 SISTEMA TIKTOK AUTÓNOMO 2026 ACTIVO")
    print("   MOTOR: Playwright (Perfil Persistente)")
    print(f"   MODO OCULTO: {'Activado' if MODO_OCULTO else 'Desactivado (Visible)'}")
    print("=============================================")
    
    # 1. Recuperar cola de archivos existentes
    recuperar_cola_perdida()
    
    # 2. Iniciar el reloj de subidas normales (Background)
    threading.Thread(target=hilo_programador_normal, daemon=True).start()
    
    # 3. Mantener el bot a la escucha
    print("[LOG] Bot de Telegram escuchando...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"[!] Error de conexión en Telegram: {e}. Reconectando en 5s...")
            time.sleep(5)

import mido
import time
import os
import sys
import socket
import threading
import importlib

# Import Flask and our MGAME engine
from flask import Flask, render_template, request, jsonify
import MGAME

# Force use of the stable backend
os.environ['MIDO_BACKEND'] = 'mido.backends.rtmidi'

HOST = '127.0.0.1'
PORT = 65432

# ==========================================================
# WEB SERVER (FLASK)
# ==========================================================
percorso_templates = r'D:\Desktop\m-game'
app = Flask(__name__, template_folder=percorso_templates)

# Forces Flask to re-read index.html from disk on every browser
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route('/')
def index():
    """Serves index.html from the Desktop project folder"""
    return render_template('index.html')

@app.route('/api/comando', methods=['POST'])
def api_universale():
    """
    Receives the function name and arguments from the browser,
    reloads MGAME.py to get the latest changes, and executes it dynamically.
    """
    dati = request.json
    nome_funzione = dati.get('funzione')
    argomenti = dati.get('args', [])
    
    try:
        # Reload MGAME.py from disk on every incoming command
        importlib.reload(MGAME)
        
        # Check if the function exists inside MGAME.py
        if hasattr(MGAME, nome_funzione):
            metodo_da_eseguire = getattr(MGAME, nome_funzione)
            # Execute the function passing the received arguments
            metodo_da_eseguire(*argomenti)
            return jsonify({"status": "ok", "msg": f"Eseguita: {nome_funzione}"})
        else:
            return jsonify({"status": "errore", "msg": f"Funzione {nome_funzione} non trovata in MGAME.py"})
    except Exception as e:
        return jsonify({"status": "errore", "msg": str(e)})

def avvia_flask():
    """Starts the web server in the background"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# ==========================================================
# MIDI ENGINE SERVER AND HANDSHAKE
# ==========================================================
def main():
    print("=== M-GAME ENGINE SERVER (FULL HOT-RELOAD ACTIVE) ===")
    
    outputs = mido.get_output_names()
    nome = next((n for n in outputs if "M-Game" in n), None)
    
    if not nome:
        print("[ERRORE] Mixer non trovato. Chiudo.")
        sys.exit()
        
    try:
        porta_midi = mido.open_output(nome)
        print(f"[OK] Connesso al driver USB: {nome}")
    except Exception as e:
        print(f"[ERRORE FATALE] Porta bloccata. Dettagli: {e}")
        sys.exit()

    # --- HARDWARE HANDSHAKE ---
    print("[INFO] Sending hardware unlock sequence...")
    p1 = [0xf0, 0x00, 0x01, 0x04, 0x05, 0x42, 0x02, 0x04, 0x01, 0x00, 0x00, 0x04, 0x03, 0x00, 0x32, 0x05, 0xf7]
    p2 = [0xf0, 0x00, 0x01, 0x04, 0x05, 0x42, 0x02, 0x04, 0x01, 0x00, 0x00, 0x04, 0x00, 0x44, 0x71, 0x05, 0xf7]
    
    porta_midi.send(mido.Message.from_bytes(p1))
    time.sleep(0.1)
    porta_midi.send(mido.Message.from_bytes(p2))
    time.sleep(0.2)
    print("[SUCCESS] Mixer unlocked!")

    # --- START WEB SERVER ---
    web_thread = threading.Thread(target=avvia_flask, daemon=True)
    web_thread.start()
    print(f"[OK] Pannello Web pronto in: {percorso_templates}")
    print("Vai su http://127.0.0.1:5000")


    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST, PORT))
        while True:
            try:
                data, addr = s.recvfrom(1024)
                msg = mido.Message.from_bytes(list(data))
                porta_midi.send(msg)
            except Exception as e:
                print(f"[!] Errore MIDI: {e}")

if __name__ == "__main__":
    main()
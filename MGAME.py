import time
import sys
import os
import socket
import math
import importlib
import json
import base64

# Database degli effetti vocali catturati (Studio Signature)
VOCAL_DB = {}
try:
    if os.path.exists('vocal_db.json'):
        with open('vocal_db.json', 'r') as f:
            VOCAL_DB = json.load(f)
            print(f"[OK] Caricati {len(VOCAL_DB)} effetti vocali dal database.")
except Exception as e:
    print(f"[ERRORE] Impossibile caricare vocal_db.json: {e}")

HOST = '127.0.0.1'
PORT = 65432

PORT_NAME = "M-Game RGB Dual"
OUTPORT = None

# PRODUCT CONFIGURATION (Use 0x42 if identifying as RGB Dual, 0x43 for some Solo firmwares)
PRODUCT_ID = 0x42

# =====================================================================
# CORE COMMUNICATION FUNCTIONS
# =====================================================================

STATE_FILE = ".mgame_state"

def load_bank_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return int(f.read().strip())
    except:
        pass
    return 0

def save_bank_state(bank):
    try:
        with open(STATE_FILE, 'w') as f:
            f.write(str(bank))
    except:
        pass

# PERSISTENT STATE - Survives Server Hot-Reloads
CURRENT_BANK = load_bank_state()

def set_active_bank(bank_index):
    global CURRENT_BANK
    CURRENT_BANK = int(bank_index)
    save_bank_state(CURRENT_BANK)
    print(f"[BANK] Active bank saved and set to: {CURRENT_BANK + 1}")

def invia_messaggio_sysex(data_array, descrizione, silente=False):
    """Sends the MIDI SysEx packet to the Server over UDP."""
    pacchetto_completo = [0xF0] + data_array + [0xF7]
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(bytes(pacchetto_completo), (HOST, PORT))
            if not silente:
                print(f"[OK] {descrizione}")
            time.sleep(0.005) # Reduced sleep for faster updates
    except Exception as e:
        print(f"[ERROR] Is the Server running? {e}")

def calcola_checksum_7bit(data_list):
    """Standard M-Game 7-bit checksum formula."""
    somma = sum(data_list)
    return (128 - (somma % 128)) & 0x7F

# =====================================================================
# LED STRIPS AND SIMPLE COMPONENTS
# =====================================================================

def imposta_led_fisso(id_led, nome, colore, lum=52):
    """Sets a static color on single-LED components (Logo, Text labels, Icons)."""
    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x03, 0x00, id_led, 0x03, 0x01, 0x00, 0x00, 0x00, 0x00, colore, 0x00, 0x00, 0x00, lum, 0x00, 0x00, 0x00]
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"{nome} -> {colore}")

def imposta_testo_animato(id_led, nome, modalita, param1, param2=0x00, param3=0x00, param4=0x00):
    """Handles Solid, Pulse (up to 4 colors) and Rainbow for 22-byte LED packets (MIC text, Logo, Icons)."""
    mod_byte = 0x00
    colori = [0x00, 0x00, 0x00, 0x00]
    lum_byte = 0x7F
    
    if modalita == 'solid':
        mod_byte = 0x00
        colori[0] = int(param1)
        lum_byte = 52 # Standard M-Game brightness level
    elif modalita == 'pulse':
        mod_byte = 0x01
        colori = [int(param1), int(param2), int(param3), int(param4)]
        lum_byte = 0x7F
    elif modalita == 'rainbow':
        mod_byte = 0x02
        alta_lum = bool(param1)
        colori[0] = 0x4D if alta_lum else 0x34
        lum_byte = 0x7F
        
    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x03, 0x00, id_led, 0x03, 0x01, mod_byte, 0x00, 0x00, 0x00]
    data_base += colori
    data_base += [lum_byte, 0x00, 0x00, 0x00]
    
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"{nome} -> {modalita}")

def imposta_strisce_led(id_striscia, colore):
    """Sets lateral LED strips (ID 0x07 Left, 0x08 Right). Uses the 26-byte rule (10 zones)."""
    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x04, 0x00, id_striscia, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00]
    data_base += [colore] * 10 + [0x00, 0x00]
    checksum = calcola_checksum_7bit(data_base)
    nome = "Strip LEFT" if id_striscia == 0x07 else "Strip RIGHT"
    invia_messaggio_sysex(data_base + [checksum], f"{nome} impostata a -> {colore}")

def imposta_fader_o_knob(id_comp, nome, indice_colore, is_knob=False):
    """Manages color for faders and the main knob."""
    stato_finale = 0x05 if is_knob else id_comp
    data_base = [0x00,0x01,0x05,PRODUCT_ID,0x00,0x04,0x00,id_comp,0x01,0x01,0x04,0x00,0x00,stato_finale,indice_colore,indice_colore,indice_colore,indice_colore,indice_colore,indice_colore,indice_colore,indice_colore,indice_colore,indice_colore,0x00,0x00]
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"{nome} -> {indice_colore}")

# =====================================================================
# MUTE / CENSOR BUTTON FUNCTIONS
# =====================================================================

def set_knob_modality_visuals(mode):
    """Updates the FX Param button LED and Main Knob ring to reflect the current mode."""
    # Main Knob LED ID (0x05) - Ring around the knob
    id_knob = 0x05

    if mode == "fx":
        # M-Game Solo: Toggle Button 0x0A logic
        imposta_funzione_knob_solo("fx")
        # Update knob ring color (Red)
        imposta_fader_o_knob(id_knob, "Main Knob (FX MODE)", 52, True)
    else:
        # M-Game Solo: Toggle Button 0x0A logic
        imposta_funzione_knob_solo("volume")
        # Update knob ring color (Blue)
        imposta_fader_o_knob(id_knob, "Main Knob (VOL MODE)", 68, True)

def imposta_volume_master_solo(val):
    """Sets the hardware volume for Main Out (Sink 0x04) on M-Game Solo."""
    # Structure: [Length 01, Src 0A (Knob), Snk 04 (Main Out), Typ 01 (Vol), P1 00, P2 Val, ...]
    header = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00]
    payload = [0x01, 0x0A, 0x04, 0x01, 0x00, val, 0x00, 0x00, 0x00]
    full = header + payload
    checksum = calcola_checksum_7bit(full)
    invia_messaggio_sysex(full + [checksum], f"Master Volume -> {val}", silente=True)

def imposta_funzione_knob_solo(mode):
    """Specific M-Game Solo sequence for switching knob mode (Source 0x0A)."""
    # Header: [F0] 00 01 05 42 00
    # Command: [Length 01, Src 0A, Snk 06, Typ 02, P1 00, P2 (0/1), P3 00, P4 00, P5 00]
    
    def _send_solo_btn(val):
        header = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00]
        # Using Src 0A (FX Param) and Snk 06 (Host Sync)
        payload = [0x01, 0x0A, 0x06, 0x02, 0x00, val, 0x00, 0x00, 0x00]
        full = header + payload
        checksum = calcola_checksum_7bit(full)
        invia_messaggio_sysex(full + [checksum], f"Solo FX Button -> {val}", silente=True)

    if mode == "fx":
        # Double packet sequence: OFF then ON
        _send_solo_btn(0x00)
        time.sleep(0.01)
        _send_solo_btn(0x01)
    else:
        # Double packet sequence: ON then OFF (to revert to Volume mode)
        _send_solo_btn(0x01)
        time.sleep(0.01)
        _send_solo_btn(0x00)

def _invia_comando_mute_base(id_tasto, nome, col_attivo, col_mutato):
    """Internal function used by Mute functions to send the SysEx packet."""
    # Updated to 0x43 for M-Game Solo
    data_base = [0x00,0x01,0x05,PRODUCT_ID,0x00,0x03,0x00,id_tasto,0x03,0x01,0x00,0x00,0x00,0x00,col_mutato,0x00,0x00,0x00,col_attivo,0x00,0x00,0x00]
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"{nome} configurato")

def imposta_tasto_fx_param_led(
    mode_inactive,
    inactive_p1,
    inactive_p2,
    inactive_p3,
    inactive_p4,
    mode_active,
    active_p1,
    active_p2,
    active_p3,
    active_p4,
):
    """
    FX PARAM button LED (RGB Dual).

    Captured frames confirm this uses the 22-byte "button" packet:
    [.. 0x03 0x01, mod, 00 00 00, inactive(4 bytes), active(4 bytes), 00 00 00, checksum]

    Current confirmed modes from captures:
    - solid: mod=0x00, inactive[0]=color, active[0]=color
    - rainbow: mod=0x02, inactive[0]=0x34 (low) or 0x4D (high); active is still a solid color
    """
    FX_PARAM_ID = 0x00

    def parse_state(mod, p1, p2, p3, p4):
        if mod == "solid":
            return 0x00, [int(p1), 0x00, 0x00, 0x00]
        if mod == "rainbow":
            # p1 is "high brightness" flag
            lum = 0x4D if str(p1).lower() in ["true", "1", "t", "high"] else 0x34
            return 0x02, [lum, 0x00, 0x00, 0x00]
        # Fallback to solid
        return 0x00, [int(p1) if str(p1).strip() else 0, 0x00, 0x00, 0x00]

    # The protocol only carries ONE mod byte; captures show it being used for the inactive state.
    mod_byte, inactive_arr = parse_state(mode_inactive, inactive_p1, inactive_p2, inactive_p3, inactive_p4)
    _, active_arr = parse_state(mode_active, active_p1, active_p2, active_p3, active_p4)

    data_base = [
        0x00, 0x01, 0x05, PRODUCT_ID, 0x00,
        0x03, 0x00, FX_PARAM_ID, 0x03, 0x01,
        mod_byte, 0x00, 0x00, 0x00,
    ]
    data_base += inactive_arr
    data_base += active_arr
    data_base += [0x00, 0x00, 0x00]

    invia_messaggio_sysex(
        data_base + [calcola_checksum_7bit(data_base)],
        f"FX Param LED -> inactive:{mode_inactive} active:{mode_active}",
    )

def imposta_tasto_mute_dinamico(id_tasto, nome, mode_off, off_p1, off_p2, off_p3, off_p4, mode_on, on_p1, on_p2, on_p3, on_p4):
    def parse_mode(mod, p1, p2, p3, p4):
        if mod == 'solid':
            return [int(p1), 0, 0, 0], 0x00
        elif mod == 'pulse':
            return [int(p1), int(p2), int(p3), int(p4)], 0x01
        elif mod == 'rainbow':
            lum = 0x4D if str(p1).lower() in ['true', '1', 't'] else 0x34
            return [lum, 0, 0, 0], 0x02
        return [0, 0, 0, 0], 0x00
        
    arr_off, byte_mod_off = parse_mode(mode_off, off_p1, off_p2, off_p3, off_p4)
    arr_on, byte_mod_on = parse_mode(mode_on, on_p1, on_p2, on_p3, on_p4)
    


    # Bank Logic: Voice FX uses ID 0x07 and 0x09 for Bank 1, but they shift to 0x14 and 0x16 for Bank 2.
    # The actual target ID changes on the hardware level, not the bank_byte at the end.
    # Standard Mutes (Mic, Censura, Sliders) use 0x00 regardless of bank.
    bank_byte = 0x00
    target_id = id_tasto

    if CURRENT_BANK == 1:
        if id_tasto == 7:  # Voice FX 1
            target_id = 0x14
        elif id_tasto == 9:  # Voice FX 2
            target_id = 0x15

    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x03, 0x00, target_id, 0x03, 0x01, byte_mod_off, 0x00, byte_mod_on, bank_byte]
    data_base += arr_off + arr_on
    
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"{nome} (Atomic Sync - Bank {CURRENT_BANK + 1})")

def imposta_tasto_mute_mic(col_on, col_off):
    _invia_comando_mute_base(0x01, "Mute Microfono", col_on, col_off)

def imposta_tasto_censura(col_on, col_off):
    _invia_comando_mute_base(0x02, "Tasto Censura", col_on, col_off)

def imposta_tasto_mute_slider(num_slider, col_on, col_off):
    id_tasto = num_slider + 2 
    _invia_comando_mute_base(id_tasto, f"Mute Slider {num_slider}", col_on, col_off)

def imposta_tasti_fx_bank(is_fx, col_on, col_off):
    id_tasto = 0x07 if is_fx else 0x08
    nome = "Voice FX 1" if is_fx else "Bank"
    _invia_comando_mute_base(id_tasto, nome, col_on, col_off)

# =====================================================================
# SAMPLER BUTTONS (3 States, Dual ID)
# =====================================================================

def imposta_tasto_sampler_dinamico(num_sample, nome, mode_un, p1_un, p2_un, p3_un, p4_un, mode_in, p1_in, p2_in, p3_in, p4_in, mode_ac, p1_ac, p2_ac, p3_ac, p4_ac):
    """
    OFFICIAL 25-BYTE SAMPLER ENGINE
    Matches Frame 748 and 19611 bit-for-bit.
    """
    if CURRENT_BANK == 0:
        id_base = 9 + int(num_sample)  # S1=10, S2=11...
    else:
        id_base = 14 + int(num_sample) # S1=15, S2=16...

    def parse_mode(m_str):
        if m_str == 'solid': return 0x00
        elif m_str == 'pulse': return 0x01
        elif m_str == 'rainbow': return 0x02
        return 0x00

    def get_color_array(m_str, p1, p2, p3, p4):
        if m_str == 'rainbow':
            # p1 defines luminosity: High (0x4D) or Low (0x34)
            return [0x4D if int(p1) else 0x34, 0x34, 0x00, 0x00]
        elif m_str == 'pulse':
            # Pulse uses all 4 bytes for alternating colors
            return [int(p1), int(p2), int(p3), int(p4)]
        else:
            # Solid uses only the first byte
            return [int(p1), 0x00, 0x00, 0x00]

    m_un = parse_mode(mode_un)
    m_in = parse_mode(mode_in)
    m_ac = parse_mode(mode_ac)

    arr_un = get_color_array(mode_un, p1_un, p2_un, p3_un, p4_un)
    arr_in = get_color_array(mode_in, p1_in, p2_in, p3_in, p4_in)
    arr_ac = get_color_array(mode_ac, p1_ac, p2_ac, p3_ac, p4_ac)

    def build_25byte_packet(m1, m2, arr1, arr2):
        # 25-byte structure confirmed from reassembled USB messages
        # [Vend_4, Zero_1, Target_3, Cmd_2, Mod_4, Col1_4, Col2_4, Checksum_1]
        d = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x03, 0x00, id_base, 0x03, 0x01]
        d += [m1, 0x00, m2, 0x00] # Params/Modifiers
        d += arr1 # Color 1 (4 bytes)
        d += arr2 # Color 2 (4 bytes)
        
        # Standard 7-bit checksum matches official dumps perfectly now
        return d + [calcola_checksum_7bit(d)]

    # Invia Inactive/Active
    invia_messaggio_sysex(build_25byte_packet(m_in, m_ac, arr_in, arr_ac), f"{nome} (Base)")
    time.sleep(0.05)
    # Invia Unassigned (sovrascrive temporaneamente il colore fisico se il Sampler è 'vuoto')
    invia_messaggio_sysex(build_25byte_packet(m_un, m_un, arr_un, arr_un), f"{nome} (Unassigned)")

# =====================================================================
# MIC INDICATOR FUNCTIONS (VU METER - 26-BYTE RULE)
# =====================================================================

def imposta_mic_indicator_solid(colore, id_slider=0):
    link = id_slider if id_slider <= 5 else 0
    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x00, 0x00, 0x00, link] 
    data_base += [colore] * 10 + [0x00, 0x00]
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"Indicator Solid ({id_slider}) -> {colore}")

def imposta_mic_indicator_custom(lista_10_colori, id_slider=0):
    link = id_slider if id_slider <= 5 else 0
    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x00, 0x00, 0x00, link] 
    data_base += lista_10_colori + [0x00, 0x00]
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"Indicator Custom Array ({id_slider})")

def imposta_mic_indicator_rainbow(alta_lum=False, id_slider=0):
    lum = 0x4D if alta_lum else 0x34
    link = id_slider if id_slider <= 5 else 0
    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x03, 0x00, 0x14, link, lum]
    data_base += [0x00] * 11
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"Indicator Rainbow ({id_slider})")

def imposta_mic_indicator_pulse(colori, id_slider=0):
    num_colori = len(colori)
    link = id_slider if id_slider <= 5 else 0
    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x01, 0x00, 0x14, link]
    data_base += colori
    data_base += [0x00] * (12 - num_colori) 
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"Indicator Pulse ({id_slider}, {num_colori} col)")

def imposta_mic_indicator_chasing(colori, id_slider=0):
    num_colori = len(colori)
    link = id_slider if id_slider <= 5 else 0
    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x02, 0x00, 0x00, link]
    data_base += colori
    data_base += [0x00] * (12 - num_colori) 
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"Indicator Chasing ({id_slider}, {num_colori} col)")

# --- UNIFIED LOGIC FOR ALL FADER MODES (Supports 10-Color Gradients) ---
def _invia_fader_base(modalita, byte12, nome_modalita, colori, colore_picco, colore_background, id_slider=0):
    if len(colori) == 1:
        colori = colori * 10
    elif len(colori) < 10:
        colori = colori + [0x00] * (10 - len(colori))
    elif len(colori) > 10:
        colori = colori[:10]
        
    link = id_slider if id_slider <= 5 else 0
    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, modalita, 0x00, byte12, link]
    data_base += colori + [colore_background, colore_picco]
    
    checksum = calcola_checksum_7bit(data_base)
    invia_messaggio_sysex(data_base + [checksum], f"Indicator {nome_modalita} ({id_slider}) (BG: {colore_background}, Picco: {colore_picco})")

def imposta_mic_indicator_fader(colori, colore_picco=0x00, colore_background=0x00, id_slider=0):
    _invia_fader_base(0x04, 0x00, "Fader", colori, colore_picco, colore_background, id_slider)

def imposta_mic_indicator_pulse_fader(colori, colore_picco=0x00, colore_background=0x00, id_slider=0):
    _invia_fader_base(0x05, 0x14, "Pulse Fader", colori, colore_picco, colore_background, id_slider)

def imposta_mic_indicator_chasing_fader(colori, colore_picco=0x00, colore_background=0x00, id_slider=0):
    _invia_fader_base(0x06, 0x00, "Chasing Fader", colori, colore_picco, colore_background, id_slider)

def imposta_mic_indicator_rainbow_fader(alta_lum=False, id_slider=0):
    lum = 0x4D if alta_lum else 0x34
    link = id_slider if id_slider <= 5 else 0
    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x07, 0x00, 0x14, link, lum]
    data_base += [0x00] * 11
    checksum = calcola_checksum_7bit(data_base)
    invia_messaggio_sysex(data_base + [checksum], f"Indicator Rainbow Fader ({id_slider})")

def imposta_mic_indicator_vu_meter(colori, colore_picco=0x00, id_slider=0):
    if len(colori) == 1:
        colori = colori * 10
    elif len(colori) != 10:
        print("[ERROR] VU Sensor requires exactly 1 or 10 colors!")
        return

    link = id_slider if id_slider <= 5 else 0
    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x38, 0x0D, 0x1E, link]
    data_base += colori + [colore_picco, 0x00]
    
    checksum = calcola_checksum_7bit(data_base)
    invia_messaggio_sysex(data_base + [checksum], f"Indicator VU Sensor ({id_slider}), Picco: {colore_picco}")
    
def imposta_numero_bank(numero, col_inactive, col_active):
    """
    Configures the two color states of the Bank number LEDs (1 and 2).
    Uses ID 0x17 for number 1 and 0x18 for number 2.
    """
    id_led = 0x17 if int(numero) == 1 else 0x18
    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x03, 0x00, id_led, 0x03, 0x01, 0x00, 0x00, 0x00, 0x00, col_inactive, 0x00, 0x00, 0x00, col_active, 0x00, 0x00, 0x00]
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"Numero Bank {numero} configurato")
    
def imposta_tasto_voice_fx_2(col_unassigned, col_inactive, col_active):
    """
    Voice FX 2 (Right side).
    Behaves exactly like a Sampler button (3 states). Base ID: 0x09, Active ID: 0x0F.
    """
    id_base = 0x09
    id_active = 0x0F

    data_base = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x03, 0x00, id_base, 0x03, 0x01, 0x00, 0x00, 0x00, 0x00, col_unassigned, 0x00, 0x00, 0x00, col_inactive, 0x00, 0x00, 0x00]
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], "Voice FX 2 (Unassigned / Inactive)")

    data_active = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x03, 0x00, id_active, 0x03, 0x01, 0x00, 0x00, 0x00, 0x00, 0x12, 0x00, 0x00, 0x00, col_active, 0x00, 0x00, 0x00]
    invia_messaggio_sysex(data_active + [calcola_checksum_7bit(data_active)], "Voice FX 2 (Active)")

# =====================================================================
# DYNAMIC GRADIENT CALCULATION
# =====================================================================

def genera_sfumatura_mgame(c1, c2):
    """
    Generates an array of 10 colors interpolating from c1 to c2.
    Integrates M-Game color wheel logic to take the shortest path
    (wrap-around on base 46-70) correctly passing through purples,
    and applies a 'glow' effect on short transitions along base bands.
    """
    sfumatura = []
    
    if c1 == 0 and c2 == 0:
        return [0]*10
        
    def decode(c):
        """Decodes the color into a circular Hue (46-70) and brightness Ring."""
        if c == 0: return 46, 0 
        h = c
        while h < 46: h += 25
        while h > 70: h -= 25
        ring = (c - h) // 25
        return h, ring

    h1, r1 = decode(c1)
    h2, r2 = decode(c2)
    
    # Wrap-around: find the shortest path along the color wheel 46-70 (range 25)
    if h2 - h1 > 12:
        h1 += 25
    elif h1 - h2 > 12:
        h2 += 25

    dist_hue = abs(h2 - h1)
    
    for i in range(10):
        # Separate Hue (H) and Ring (R) interpolation
        h_float = h1 + (h2 - h1) * (i / 9.0)
        r_float = r1 + (r2 - r1) * (i / 9.0)
        
        r_glow = 0
        if r1 == r2 == 0 and (2 < i < 7) and dist_hue <= 12:
            r_glow = 1
            
        r_finale = int(round(r_float)) + r_glow
        h_round = int(round(h_float))
        
        h_wrapped = ((h_round - 46) % 25) + 46
        
        if h_wrapped == 51:
            h_wrapped = 50
            
        val = h_wrapped + (r_finale * 25)
        
        if val > 127: val = 127
        if val < 0: val = 0
            
        sfumatura.append(val)
        
    # Accurately force the endpoint values
    sfumatura[0] = c1
    sfumatura[9] = c2
    return sfumatura

def imposta_mic_indicator_dynamic_gradient(c1, c2, is_fader=True, colore_picco=0x00, colore_background=0x00, id_slider=0):
    """Generates a perfect dynamic gradient via the recreated algorithm and sends it."""
    array_sfumatura = genera_sfumatura_mgame(c1, c2)
    modalita = 0x04 if is_fader else 0x00
    nome_mod = "Fader" if is_fader else "Solid"
    _invia_fader_base(modalita, 0x00, f"Dynamic Gradient {nome_mod} ({c1}->{c2})", array_sfumatura, colore_picco, colore_background, id_slider)

# =====================================================================
# AUDIO DSP CONTROLS
# =====================================================================

def imposta_mic_dsp(gain, hz):
    import math
    # Gain Booster (0 to 12 dB) mapped on base 115
    gain_val = int(115 + max(0, min(12, int(gain))))
    
    hz = max(15, min(1000, int(hz)))
    
    # Exact exponential conversion formula for the M-Game hardware:
    # val = 17.35 * ln(Hz / 15.0)
    val_hpf = int(round(17.35 * math.log(hz / 15.0)))
    val_hpf = max(0, min(127, val_hpf))
                
    data = [0x00,0x01,0x05,0x42,0x00,0x03,0x00,0x00,0x01,0x41,0x01, gain_val, 0x02,0x00,0x00,0x09, val_hpf, 0x00,0x00,0x00,0x00,0x00]
    invia_messaggio_sysex(data + [calcola_checksum_7bit(data)], f"DSP Mic (Boost: {gain}dB, HPF: {hz}Hz)")

def imposta_noise_gate(db):
    val = max(0, min(127, db + 127))
    data = [0x00,0x01,0x05,0x42,0x00,0x01,0x00,0x00,0x02,0x41,0x4D,0x00,0x46,val]
    invia_messaggio_sysex(data + [calcola_checksum_7bit(data)], f"Noise Gate (Soglia): {db}dB")

def imposta_de_esser(val):
    val = max(0, min(127, int(val)))
    data = [
        0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x07, 0x00, 0x00,
        0x09, 0x41, 0x01, 0x73, 0x01, 0x00, 0x40, 
        0x07, 0x55, 0x00, 0x01, 0x73, 0x02, 0x00, 
        0x40, 0x07, 0x4e, 0x00, 0x01, 0x07, val, 
        0x57, 0x0f, 0x06, 0x00, 0x00, 0x74, 0x73, 
        0x01, 0x00
    ]
    invia_messaggio_sysex(data + [calcola_checksum_7bit(data)], f"De-Esser: {val}")

def imposta_compressor(attivo, amount):
    stato = 1 if attivo else 0
    val = max(0, min(127, int(amount)))
    
    # Byte 11 controls the "real" % compression, replicate on byte 12 as tested with low values
    data = [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x02, 0x00, 0x00, 
            0x06, 0x41, stato, val, val, 0x57, 0x02, 0x04, 0x00, 0x00]
    invia_messaggio_sysex(data + [calcola_checksum_7bit(data)], f"Compressor: {'ON' if attivo else 'OFF'} ({val})")

def imposta_eq(attivo, low, mid, high):
    stato = 1 if attivo else 0
    # Each MIDI step corresponds to 0.25 dB (64 = 0 dB)
    val_l = max(0, min(127, int(64 + (float(low) * 4))))
    val_m = max(0, min(127, int(64 + (float(mid) * 4))))
    val_h = max(0, min(127, int(64 + (float(high) * 4))))
    
    data = [0x00,0x01,0x05,0x42,0x00,0x07,0x00,0x00, 
            0x05, 0x41, stato, 0x73, 0x09, 0x05, 0x05, 0x05, 
            0x0a, 0x00, val_l, 0x00, 0x1d, 0x00, 0x40, 0x01, 
            0x31, 0x00, val_m, 0x01, 0x47, 0x00, 0x40, 0x01, 
            0x61, 0x00, val_h, 0x01, 0x66, 0x00]
            
    invia_messaggio_sysex(data + [calcola_checksum_7bit(data)], f"EQ: {'ON' if attivo else 'OFF'} (L:{low} M:{mid} H:{high})")

# =====================================================================
# MAIN MENU
# =====================================================================

def main():
    while True:
        print("\n" + "█"*54)
        print("         M-GAME RGB DUAL - MASTER CONTROL V20 OUTDATED USE THE WEBPAGE")
        print("█"*54)
        print(" 1. Logo (Colore)           2. Testo MIC (Colore)")
        print("22. Icona Controller (Col) 23. Icona Chat (Colore)")
        print("24. Icona Sampler (Colore) 25. Testo CONTENT (Col)")
        print("26. Icona System (Colore)   3. Strisce LED (SX/DX)")
        print(" 4. Main Knob (Colore)      5. Slider Colori (1-4)")
        print(" 6. Tasti Mute / Censura    7. Tasti Sampler (1-5)")
        print(" 8. Voice FX 1 & Bank")
        print("\n --- MIC INDICATOR (10 LED) ---")
        print(" 9. Solid Color            10. Sfumatura/Pattern")
        print("11. Rainbow Animato        12. Pulse (1-4 Colori)")
        print("13. Chasing (1-4 Colori)   14. Fader VU Meter")
        print("15. Gradient Fader (Preset)16. Pulse Fader (1-4 Col)")
        print("17. Chasing Fader (1-2 Col)18. Rainbow Fader")
        print("19. VU Sensor (Sensore Mic)")
        print("\n --- AUDIO & DSP ---")
        print("20. Mic Boost (0-12)       21. Noise Gate (dB)")
        print("\n 0. ESCI")
        print("█"*54)

        scelta = input("\nSeleziona opzione: ")

        try:
            if scelta == '1': imposta_led_fisso(0x19, "Logo", int(input("Colore: ")))
            elif scelta == '2': imposta_led_fisso(0x1A, "Testo MIC", int(input("Colore: ")))
            elif scelta == '22': imposta_led_fisso(0x1D, "Icona Controller", int(input("Colore: ")))
            elif scelta == '23': imposta_led_fisso(0x1E, "Icona Chat", int(input("Colore: ")))
            elif scelta == '24': imposta_led_fisso(0x1F, "Icona Sampler", int(input("Colore: ")))
            elif scelta == '25': imposta_led_fisso(0x1C, "Testo CONTENT", int(input("Colore: ")))
            elif scelta == '26': imposta_led_fisso(0x20, "Icona System", int(input("Colore: ")))
            
            elif scelta == '3':
                sd = int(input("1=SX, 2=DX: "))
                id_striscia = 0x07 if sd == 1 else 0x08
                imposta_strisce_led(id_striscia, int(input("Colore (es. 52 Rosso, 68 Blu): ")))
                
            elif scelta == '4': imposta_fader_o_knob(0x05, "Main Knob", int(input("Colore: ")), True)
            
            elif scelta == '5':
                idx = int(input("Slider (1-4): "))
                imposta_fader_o_knob(idx, f"Slider {idx}", int(input("Colore: ")))
                
            elif scelta == '6':
                print("\n--- IMPOSTAZIONI MUTE ---")
                print("1. Mute Microfono\n2. Tasto Censura\n3. Mute Slider 1\n4. Mute Slider 2\n5. Mute Slider 3\n6. Mute Slider 4")
                sub = input("Tasto da configurare (1-6): ")
                c_on = int(input("Colore ON: "))
                c_off = int(input("Colore OFF: "))
                if sub == '1': imposta_tasto_mute_mic(c_on, c_off)
                elif sub == '2': imposta_tasto_censura(c_on, c_off)
                elif sub in ['3', '4', '5', '6']:
                    imposta_tasto_mute_slider(int(sub) - 2, c_on, c_off)
                    
            elif scelta == '7':
                idx = int(input("Sample (1-5): "))
                imposta_tasto_sampler(idx, f"S{idx}", int(input("Col Unassigned: ")), int(input("Col Inactive: ")), int(input("Col Active: ")))
                
            elif scelta == '8':
                sub = input("1 per Voice FX 1, 2 per Bank: ")
                imposta_tasti_fx_bank((sub == '1'), int(input("Col ON: ")), int(input("Col OFF: ")))
            
            elif scelta == '9': imposta_mic_indicator_solid(int(input("Colore: ")))
            elif scelta == '10':
                cols = [int(x) for x in input("Inserisci 10 colori (es. 68,52,68...): ").split(",")]
                imposta_mic_indicator_custom(cols)
            elif scelta == '11': imposta_mic_indicator_rainbow(input("Lum alta? (s/n): ").lower() == 's')
            elif scelta == '12':
                cols = [int(x) for x in input("Inserisci da 1 a 4 colori separati da virgola: ").split(",")]
                imposta_mic_indicator_pulse(cols)
                
            elif scelta == '13':
                cols = [int(x) for x in input("Inserisci da 1 a 4 colori separati da virgola (es. 52,68): ").split(",")]
                imposta_mic_indicator_chasing(cols)

            elif scelta == '14':
                print("SINTASSI: [Colori Base] | [Colore Picco] | [Colore Background]")
                input_str = input("Inserisci configurazione: ")
                try:
                    parti = input_str.split("|")
                    parte_base = parti[0]
                    if "," in parte_base:
                        cols = [int(x.strip()) for x in parte_base.split(",")]
                    else:
                        cols = [int(parte_base.strip())]
                    col_picco = int(parti[1].strip()) if len(parti) > 1 else 0x00
                    col_bg = int(parti[2].strip()) if len(parti) > 2 else 0x00
                    imposta_mic_indicator_fader(cols, col_picco, col_bg)
                except Exception as e:
                    print(f"Errore di sintassi. Dettagli: {e}")

            elif scelta == '15':
                print("\n--- PRESET GRADIENTI FADER ---")
                nomi = list(GRADIENTI_SALVATI.keys())
                for i, nome in enumerate(nomi):
                    print(f"{i+1}. {nome}")
                sel = input("Scegli il numero del Preset: ")
                try:
                    sel_preset = int(sel) - 1
                    if 0 <= sel_preset < len(nomi):
                        c_picco = input("Colore Picco (Invio per nessuno): ")
                        c_bg = input("Colore Background (Invio per nessuno): ")
                        p_val = int(c_picco) if c_picco.strip() else 0x00
                        b_val = int(c_bg) if c_bg.strip() else 0x00
                        imposta_fader_preset(nomi[sel_preset], p_val, b_val)
                    else:
                        print("Scelta non valida.")
                except ValueError:
                    print("Inserisci un numero valido.")

            elif scelta == '16':
                cols = [int(x.strip()) for x in input("Colori (1-4): ").split(",")]
                imposta_mic_indicator_pulse_fader(cols)
                
            elif scelta == '17':
                cols = [int(x.strip()) for x in input("Colori (1-2): ").split(",")]
                imposta_mic_indicator_chasing_fader(cols)

            elif scelta == '18':
                risp = input("Vuoi la luminosità ALTA? (s/n): ")
                imposta_mic_indicator_rainbow_fader(risp.lower() == 's')

            elif scelta == '19':
                print("SINTASSI: [Colori Base] | [Colore Picco]")
                input_str = input("Inserisci configurazione: ")
                try:
                    if "|" in input_str:
                        parti = input_str.split("|")
                        parte_base = parti[0]
                        col_picco = int(parti[1].strip())
                    else:
                        parte_base = input_str
                        col_picco = 0x00
                    if "," in parte_base:
                        cols = [int(x.strip()) for x in parte_base.split(",")]
                    else:
                        cols = [int(parte_base.strip())]
                    imposta_mic_indicator_vu_meter(cols, col_picco)
                except Exception as e:
                    print(f"Errore di sintassi: {e}")

            elif scelta == '20': imposta_mic_boost(int(input("Boost (0-12): ")))
            elif scelta == '21': imposta_noise_gate(int(input("Gate dB: ")))
            elif scelta == '0': sys.exit(0)
        except Exception as e: print(f"Errore: {e}")

import base64

# =====================================================================
# VOICE EFFECTS ENGINE
# =====================================================================

VOICE_FX_TEMPLATE = {
    0x00: [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x10, 0x00, 0x00, 0x03, 0x50, 0x00, 0x00, 0x00, 0x41, 0x5a, 0x00, 0x10, 0x00, 0x01, 0x00, 0x00, 0x41, 0x19, 0x19, 0x34, 0x00, 0x02, 0x00, 0x00, 0x41, 0x66, 0x00, 0x34, 0x10, 0x03, 0x00, 0x00, 0x41, 0x05, 0x00, 0x20, 0x00, 0x04, 0x00, 0x00, 0x41, 0x53, 0x00, 0x34, 0x00, 0x05, 0x00, 0x00, 0x41, 0x00, 0x00, 0x20, 0x00, 0x06, 0x00, 0x00, 0x41, 0x3f, 0x00, 0x34, 0x00, 0x07, 0x00, 0x00, 0x41, 0x00, 0x00, 0x20, 0x00, 0x00],
    0x10: [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x10, 0x10, 0x00, 0x03, 0x50, 0x08, 0x00, 0x00, 0x41, 0x3f, 0x00, 0x34, 0x00, 0x09, 0x00, 0x00, 0x41, 0x00, 0x00, 0x20, 0x00, 0x0a, 0x00, 0x00, 0x41, 0x3f, 0x00, 0x34, 0x00, 0x00, 0x00, 0x04, 0x41, 0x1e, 0x00, 0x00, 0x3f, 0x00, 0x00, 0x07, 0x41, 0x01, 0x7f, 0x0b, 0x69, 0x01, 0x00, 0x07, 0x41, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x07, 0x41, 0x38, 0x0c, 0x7f, 0x7f, 0x03, 0x00, 0x07, 0x41, 0x00, 0x00, 0x00, 0x00, 0x00],
    0x20: [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x10, 0x20, 0x00, 0x03, 0x50, 0x04, 0x00, 0x07, 0x41, 0x02, 0x46, 0x00, 0x1d, 0x05, 0x00, 0x07, 0x41, 0x02, 0x5d, 0x50, 0x4a, 0x00, 0x00, 0x08, 0x41, 0x00, 0x67, 0x73, 0x01, 0x00, 0x03, 0x04, 0x01, 0x02, 0x00, 0x00, 0x41, 0x01, 0x03, 0x04, 0x01, 0x7f, 0x00, 0x00, 0x00, 0x02, 0x03, 0x04, 0x01, 0x59, 0x00, 0x00, 0x00, 0x03, 0x03, 0x04, 0x01, 0x6d, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x4e, 0x41, 0x4d, 0x45, 0x00],
    0x30: [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x10, 0x30, 0x00, 0x03, 0x50, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    0x40: [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x10, 0x40, 0x00, 0x03, 0x50, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    0x50: [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x10, 0x50, 0x00, 0x03, 0x50, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    0x60: [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x10, 0x60, 0x00, 0x03, 0x50, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    0x70: [0x00, 0x01, 0x05, PRODUCT_ID, 0x00, 0x10, 0x70, 0x00, 0x03, 0x50, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
}

def interpol(val, min_hex, max_hex):
    # val is 0-100
    val = max(0, min(100, val))
    return int(min_hex + (max_hex - min_hex) * (val / 100.0))

def costruisci_payload_effetti(preset_name,
                        vocal_on, vocal_dial, vocal_id,
                        dist_on, dist_dial, dist_id,
                        chorus_on, chorus_dial, chorus_id,
                        reverb_on, reverb_dial, reverb_id):
    
    # Se l'utente ha selezionato un effetto mappato nel DB, usiamo quello come base
    if vocal_id in VOCAL_DB:
        pacchetti_raw = VOCAL_DB[vocal_id]
        # Convertiamo le chiavi da stringa "00" a intero 0x00
        pacchetti = {int(k, 16): list(v) for k, v in pacchetti_raw.items()}
    else:
        pacchetti = {k: list(v) for k, v in VOICE_FX_TEMPLATE.items()}
        # Se non è nel DB, vocal_id potrebbe essere un numero
        try:
            pacchetti[0x00][18] = int(vocal_id)
        except:
            pass
    
    # Enforce PRODUCT_ID for Solo (0x43) even if DB says 0x42
    for k in pacchetti:
        pacchetti[k][3] = PRODUCT_ID
        
    # Override: Nome Preset
    b64_name = base64.b64encode(preset_name.encode('utf-8')).decode('ascii')
    for i in range(len(b64_name)):
        if 10 + i < 74: 
            pacchetti[0x30][10 + i] = ord(b64_name[i])
    
    # Override: Toggles e Intensità
    # Nota: Usiamo gli stessi offset di prima, ma sopra la base "Studio"
    pacchetti[0x00][14] = 0x5b if vocal_on else 0x5a
    pacchetti[0x00][30] = interpol(vocal_dial, 0x59, 0x6d)
    
    # Distortion (se non mappato nel DB specifico per distorsione, usiamo ID generico)
    # pacchetti[0x10][39] = dist_id  # Commentato per ora se usiamo signatures globali
    dist_val = interpol(dist_dial, 0x00, 0x1e)
    pacchetti[0x10][38] = (dist_val << 1) | (1 if dist_on else 0)
    
    # Chorus
    pacchetti[0x20][14] = 0x03 if chorus_on else 0x02
    pacchetti[0x20][31] = interpol(chorus_dial, 0x5f, 0x6d)
    
    # Reverb
    pacchetti[0x20][30] = interpol(reverb_dial, 0x5a, 0x69) if reverb_on else 0x00
        
    for k in sorted(pacchetti.keys()):
        data = pacchetti[k][:74] 
        pacchetti[k][74] = calcola_checksum_7bit(data)
        
    return pacchetti

def invia_voice_effects(preset_name,
                        vocal_on, vocal_dial, vocal_id,
                        dist_on, dist_dial, dist_id,
                        chorus_on, chorus_dial, chorus_id,
                        reverb_on, reverb_dial, reverb_id,
                        quick_update=False, segments=None):
    
    # Se quick_update è attivo, saltiamo il refresh OFF/ON e inviamo solo i segmenti richiesti
    if quick_update:
        pacchetti = costruisci_payload_effetti(preset_name,
                            vocal_on, vocal_dial, vocal_id,
                            dist_on, dist_dial, dist_id,
                            chorus_on, chorus_dial, chorus_id,
                            reverb_on, reverb_dial, reverb_id)
        
        target_keys = segments if segments is not None else sorted(pacchetti.keys())
        for k in target_keys:
            if k in pacchetti:
                invia_messaggio_sysex(pacchetti[k], f"Voice FX QUICK {k:02x}", silente=True)
        return

    # HARDWARE REFRESH FIX:
    # Il mixer non ricarica i parametri audio interni a meno che l'effetto non venga "ciclato".
    # Inviamo prima un pacchetto "Tutto Spento" per forzare lo scaricamento dalla memoria...
    pacchetti_spenti = costruisci_payload_effetti(preset_name,
                        False, vocal_dial, vocal_id,
                        False, dist_dial, dist_id,
                        False, chorus_dial, chorus_id,
                        False, reverb_dial, reverb_id)
    
    for k in sorted(pacchetti_spenti.keys()):
        invia_messaggio_sysex(pacchetti_spenti[k], f"Voice FX OFF {k:02x}")
        
    # Aspettiamo 50ms per dare il tempo al mixer di staccare i relay/DSP interni
    time.sleep(0.05)
    
    # ...e poi inviamo il pacchetto vero con i toggle ON richiesti dall'utente!
    pacchetti_finali = costruisci_payload_effetti(preset_name,
                        vocal_on, vocal_dial, vocal_id,
                        dist_on, dist_dial, dist_id,
                        chorus_on, chorus_dial, chorus_id,
                        reverb_on, reverb_dial, reverb_id)
                        
    for k in sorted(pacchetti_finali.keys()):
        invia_messaggio_sysex(pacchetti_finali[k], f"Voice FX FINAL {k:02x}")

if __name__ == "__main__":
    main()
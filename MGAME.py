import time
import sys
import socket
import math
import importlib

HOST = '127.0.0.1'
PORT = 65432

PORT_NAME = "M-Game RGB Dual"
OUTPORT = None

# =====================================================================
# CORE COMMUNICATION FUNCTIONS
# =====================================================================

try:
    CURRENT_BANK
except NameError:
    CURRENT_BANK = 0 # 0 = Bank 1, 1 = Bank 2

def set_active_bank(bank_index):
    global CURRENT_BANK
    CURRENT_BANK = int(bank_index)
    print(f"[BANK] Active bank set to: {CURRENT_BANK + 1}")

def invia_messaggio_sysex(data_array, descrizione):
    """Sends the MIDI SysEx packet to the Server over UDP."""
    pacchetto_completo = [0xF0] + data_array + [0xF7]
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(bytes(pacchetto_completo), (HOST, PORT))
            print(f"[OK] {descrizione}")
            time.sleep(0.01)
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
    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x03, 0x00, id_led, 0x03, 0x01, 0x00, 0x00, 0x00, 0x00, colore, 0x00, 0x00, 0x00, lum, 0x00, 0x00, 0x00]
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
        
    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x03, 0x00, id_led, 0x03, 0x01, mod_byte, 0x00, 0x00, 0x00]
    data_base += colori
    data_base += [lum_byte, 0x00, 0x00, 0x00]
    
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"{nome} -> {modalita}")

def imposta_strisce_led(id_striscia, colore):
    """Sets lateral LED strips (ID 0x07 Left, 0x08 Right). Uses the 26-byte rule (10 zones)."""
    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x04, 0x00, id_striscia, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00]
    data_base += [colore] * 10 + [0x00, 0x00]
    checksum = calcola_checksum_7bit(data_base)
    nome = "Strip LEFT" if id_striscia == 0x07 else "Strip RIGHT"
    invia_messaggio_sysex(data_base + [checksum], f"{nome} impostata a -> {colore}")

def imposta_fader_o_knob(id_comp, nome, indice_colore, is_knob=False):
    """Manages color for faders and the main knob."""
    stato_finale = 0x05 if is_knob else id_comp
    data_base = [0x00,0x01,0x05,0x42,0x00,0x04,0x00,id_comp,0x01,0x01,0x04,0x00,0x00,stato_finale,indice_colore,indice_colore,indice_colore,indice_colore,indice_colore,indice_colore,indice_colore,indice_colore,indice_colore,indice_colore,0x00,0x00]
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"{nome} -> {indice_colore}")

# =====================================================================
# MUTE / CENSOR BUTTON FUNCTIONS
# =====================================================================

def _invia_comando_mute_base(id_tasto, nome, col_attivo, col_mutato):
    """Internal function used by Mute functions to send the SysEx packet."""
    data_base = [0x00,0x01,0x05,0x42,0x00,0x03,0x00,id_tasto,0x03,0x01,0x00,0x00,0x00,0x00,col_mutato,0x00,0x00,0x00,col_attivo,0x00,0x00,0x00]
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"{nome} configurato")

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

    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x03, 0x00, target_id, 0x03, 0x01, byte_mod_off, 0x00, byte_mod_on, bank_byte]
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
    Configures the 3 states of Sampler buttons using the exact hardware logic.
    There is no secondary ID for unassigned states. 
    id_base covers ALL 3 states based on modifier masks!
    """
    if CURRENT_BANK == 0:
        id_base = 9 + int(num_sample)       # Sample 1-5 Bank 1: 10-14 (0x0A - 0x0E)
    else:
        id_base = 14 + int(num_sample)      # Sample 1-5 Bank 2: 15-19 (0x0F - 0x13)

    def _get_bytes(mode, p1, p2, p3, p4):
        if mode == "rainbow":
            return 0x02, [0x4D if p1 else 0x34, 0x34, 0x00, 0x00]
        elif mode == "pulse":
            return 0x01, [p1, p2, p3, p4]
        else: # solid
            return 0x00, [p1, 0x00, 0x00, 0x00]

    mod_un, cols_un = _get_bytes(mode_un, p1_un, p2_un, p3_un, p4_un)
    mod_in, cols_in = _get_bytes(mode_in, p1_in, p2_in, p3_in, p4_in)
    mod_ac, cols_ac = _get_bytes(mode_ac, p1_ac, p2_ac, p3_ac, p4_ac)

    # 1. Inactive/Active packet usa lo stesso ID!
    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x03, 0x00, id_base, 0x03, 0x01, mod_in, 0x00, mod_ac, 0x00] + cols_in + cols_ac
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"{nome} (Inactive/Active - Bank {CURRENT_BANK + 1})")

    time.sleep(0.05) # Lascia al mixer il tempo di salvare il primo pacchetto

    # L'hardware imposta lo stato Unassigned quando i byte di modalità sono entrambi 0x02 per il pacchetto primario
    # Deve essere mandato SECONDO, altrimenti il pacchetto base Inactive lo sovrascrive o l'hardware lo droppa!
    # L'array colori per Unassigned DEVE essere formattato come [Colore, 0, 0, 0] indipendentemente dalle scelte UI
    col_un_fixed = [cols_un[0], 0x00, 0x00, 0x00]
    data_unassigned = [0x00, 0x01, 0x05, 0x42, 0x00, 0x03, 0x00, id_base, 0x03, 0x01, 0x02, 0x00, 0x02, 0x00] + col_un_fixed + col_un_fixed
    invia_messaggio_sysex(data_unassigned + [calcola_checksum_7bit(data_unassigned)], f"{nome} (Unassigned - Bank {CURRENT_BANK + 1})")

# =====================================================================
# MIC INDICATOR FUNCTIONS (VU METER - 26-BYTE RULE)
# =====================================================================

def imposta_mic_indicator_solid(colore, id_slider=0):
    link = id_slider if id_slider <= 5 else 0
    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x00, 0x00, 0x00, link] 
    data_base += [colore] * 10 + [0x00, 0x00]
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"Indicator Solid ({id_slider}) -> {colore}")

def imposta_mic_indicator_custom(lista_10_colori, id_slider=0):
    link = id_slider if id_slider <= 5 else 0
    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x00, 0x00, 0x00, link] 
    data_base += lista_10_colori + [0x00, 0x00]
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"Indicator Custom Array ({id_slider})")

def imposta_mic_indicator_rainbow(alta_lum=False, id_slider=0):
    lum = 0x4D if alta_lum else 0x34
    link = id_slider if id_slider <= 5 else 0
    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x03, 0x00, 0x14, link, lum]
    data_base += [0x00] * 11
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"Indicator Rainbow ({id_slider})")

def imposta_mic_indicator_pulse(colori, id_slider=0):
    num_colori = len(colori)
    link = id_slider if id_slider <= 5 else 0
    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x01, 0x00, 0x14, link]
    data_base += colori
    data_base += [0x00] * (12 - num_colori) 
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"Indicator Pulse ({id_slider}, {num_colori} col)")

def imposta_mic_indicator_chasing(colori, id_slider=0):
    num_colori = len(colori)
    link = id_slider if id_slider <= 5 else 0
    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x02, 0x00, 0x00, link]
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
    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, modalita, 0x00, byte12, link]
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
    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x07, 0x00, 0x14, link, lum]
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
    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x04, 0x00, id_slider, 0x01, 0x01, 0x38, 0x0D, 0x1E, link]
    data_base += colori + [colore_picco, 0x00]
    
    checksum = calcola_checksum_7bit(data_base)
    invia_messaggio_sysex(data_base + [checksum], f"Indicator VU Sensor ({id_slider}), Picco: {colore_picco}")
    
def imposta_numero_bank(numero, col_inactive, col_active):
    """
    Configures the two color states of the Bank number LEDs (1 and 2).
    Uses ID 0x17 for number 1 and 0x18 for number 2.
    """
    id_led = 0x17 if int(numero) == 1 else 0x18
    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x03, 0x00, id_led, 0x03, 0x01, 0x00, 0x00, 0x00, 0x00, col_inactive, 0x00, 0x00, 0x00, col_active, 0x00, 0x00, 0x00]
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], f"Numero Bank {numero} configurato")
    
def imposta_tasto_voice_fx_2(col_unassigned, col_inactive, col_active):
    """
    Voice FX 2 (Right side).
    Behaves exactly like a Sampler button (3 states). Base ID: 0x09, Active ID: 0x0F.
    """
    id_base = 0x09
    id_active = 0x0F

    data_base = [0x00, 0x01, 0x05, 0x42, 0x00, 0x03, 0x00, id_base, 0x03, 0x01, 0x00, 0x00, 0x00, 0x00, col_unassigned, 0x00, 0x00, 0x00, col_inactive, 0x00, 0x00, 0x00]
    invia_messaggio_sysex(data_base + [calcola_checksum_7bit(data_base)], "Voice FX 2 (Unassigned / Inactive)")

    data_active = [0x00, 0x01, 0x05, 0x42, 0x00, 0x03, 0x00, id_active, 0x03, 0x01, 0x00, 0x00, 0x00, 0x00, 0x12, 0x00, 0x00, 0x00, col_active, 0x00, 0x00, 0x00]
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
        0x00, 0x01, 0x05, 0x42, 0x00, 0x07, 0x00, 0x00,
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
    data = [0x00, 0x01, 0x05, 0x42, 0x00, 0x02, 0x00, 0x00, 
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

if __name__ == "__main__":
    main()
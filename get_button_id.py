import mido
import time

def main():
    print("=== M-GAME HARDWARE SCANNER ===")
    inputs = mido.get_input_names()
    nome = next((n for n in inputs if "M-Game" in n), None)
    
    if not nome:
        print("[ERRORE] Mixer non trovato.")
        return
        
    print(f"[OK] In ascolto su: {nome}")
    print("AZIONI RICHIESTE:")
    print("1. GIRA LA MANOPOLA CENTRALE (Knob) -> Voglio vedere il segnale di rotazione.")
    print("2. PREMI IL TASTO 'FX PARAM' (quello che non funziona) -> Voglio vedere il segnale del tasto.")
    print("3. PREMI UN TASTO VOICE FX (es. FX 1) -> Per confronto.\n")
    
    try:
        with mido.open_input(nome) as inport:
            for msg in inport:
                data = msg.bytes()
                if msg.type == 'sysex':
                    # Header: F0 00 01 05 42 00 ...
                    hex_data = " ".join(f"{b:02x}" for b in data)
                    
                    if len(data) >= 10:
                        src = data[7]
                        snk = data[8]
                        typ = data[9]
                        p1 = data[10] if len(data) > 10 else 0
                        p2 = data[11] if len(data) > 11 else 0
                        
                        if typ == 0x01: # Volume Change / Knob
                            print(f"[KNOB/SLIDER] Src: {src:02x}, Snk: {snk:02x}, Val: {p2:02x} ({p2})")
                        elif typ == 0x02: # Button
                            print(f"[BUTTON] Src: {src:02x}, Snk: {snk:02x}, P1: {p1:02x}, P2: {p2:02x}")
                        else:
                            print(f"[SYSEX {typ:02x}] {hex_data}")
                    else:
                        print(f"[SHORT SYSEX] {hex_data}")
                        
                elif msg.type == 'control_change':
                    print(f"[CC] {msg.control} -> {msg.value}")
                else:
                    print(f"[OTHER] {msg}")
                    
    except KeyboardInterrupt:
        print("\nChiusura.")

if __name__ == "__main__":
    main()

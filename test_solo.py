import mido
import time

def calcola_checksum(data):
    return (128 - (sum(data) % 128)) & 0x7F

def invia_payload(outport, length, src, snk, typ, p2):
    header = [0x00, 0x01, 0x05, 0x43, 0x00]
    # Struttura Short (10 byte): Header + Length(01) + Src + Snk + Typ + P1 + P2 + P3 + P4 + P5
    payload = [length, src, snk, typ, 0x00, p2, 0x00, 0x00, 0x00]
    full_msg = header + payload
    msg = [0xF0] + full_msg + [calcola_checksum(full_msg), 0xF7]
    outport.send(mido.Message.from_bytes(msg))
    time.sleep(0.1)

if __name__ == "__main__":
    outputs = mido.get_output_names()
    nome = next((n for n in outputs if "M-Game" in n), None)
    if nome:
        with mido.open_output(nome) as out:
            # TEST 1: ID 0x00 (Quello che hai visto tu) con diversi Sink
            print("Test 1: Componente 0x00 (possibile FX Param)...")
            for s in [0x00, 0x06, 0x0A]:
                invia_payload(out, 0x01, 0x00, s, 0x02, 0x01) # Tipo Button
                invia_payload(out, 0x01, 0x00, s, 0x04, 0x01) # Tipo VoiceFX
            
            # TEST 2: ID 0x0E (VoiceFX ID ufficiale dal protocollo)
            print("Test 2: Componente 0x0E (VoiceFX)...")
            invia_payload(out, 0x01, 0x0E, 0x00, 0x02, 0x01)
            
            # TEST 3: ID 0x0A (Main Knob ID ufficiale input)
            print("Test 3: Componente 0x0A (Knob)...")
            invia_payload(out, 0x01, 0x0A, 0x00, 0x01, 0x40) # Prova a cambiare colore
            
            print("Fine test. Qualcosa si è illuminato?")
    else:
        print("Mixer non trovato.")

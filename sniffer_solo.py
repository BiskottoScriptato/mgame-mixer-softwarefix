import mido
import time

def calcola_checksum(data):
    return (128 - (sum(data) % 128)) & 0x7F

def invia_led_25(outport, id_tasto, r, g, b):
    # Struttura catturata dai campioni del protocollo (25 byte)
    header = [0x00, 0x01, 0x05, 0x42, 0x00] # Dual PID
    # Lunghezza 03, Source 00, Sink id_tasto, Tipo 03, poi i colori
    # Il payload tipico è 01 00 00 00 00 [R] [G] [B] ...
    payload = [0x03, 0x00, id_tasto, 0x03, 0x01, 0x00, 0x00, 0x00, 0x00, r, g, b, 0x00, 0x7F, 0x00, 0x00, 0x00]
    
    full = header + payload
    msg = [0xF0] + full + [calcola_checksum(full), 0xF7]
    outport.send(mido.Message.from_bytes(msg))
    print(f"Inviato LED Update a ID {id_tasto:02x}")

if __name__ == "__main__":
    outputs = mido.get_output_names()
    nome = next((n for n in outputs if "M-Game" in n), None)
    if nome:
        with mido.open_output(nome) as out:
            print("Test LED per FX Param...")
            # Proviamo gli ID 0x00 e 0x0A che sono i più probabili
            invia_led_25(out, 0x00, 0x7F, 0x00, 0x00) # Rosso
            time.sleep(0.1)
            invia_led_25(out, 0x0A, 0x00, 0x7F, 0x00) # Verde
            print("Qualche tasto ha cambiato colore (Rosso o Verde)?")
    else:
        print("Mixer non trovato.")

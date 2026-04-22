import mido

def main():
    print("=== M-GAME VOCAL ID MAPPER ===")
    inputs = mido.get_input_names()
    nome = next((n for n in inputs if "M-Game" in n), None)
    
    if not nome:
        print("[ERRORE] Mixer non trovato tra i dispositivi di input MIDI.")
        print(f"Dispositivi trovati: {inputs}")
        return
        
    print(f"[OK] In ascolto su: {nome}")
    print("ISTRUZIONI:")
    print("1. Tieni aperto questo script.")
    print("2. Apri il SOFTWARE UFFICIALE M-Game.")
    print("3. Cambia l'effetto Vocal Processor dal menu a tendina e guarda questa finestra!")
    print("Premi Ctrl+C per uscire.\n")
    
    # Memorizziamo l'ultimo stato di tutti gli 8 pacchetti (0x00, 0x10, ... 0x70)
    last_packets = {i: None for i in range(0, 0x80, 0x10)}
    
    try:
        with mido.open_input(nome) as inport:
            for msg in inport:
                if msg.type == 'sysex':
                    data = msg.bytes()
                    # Header M-Game: F0 00 01 05 42 00 10 00
                    if len(data) >= 70 and data[1:6] == [0x00, 0x01, 0x05, 0x42, 0x00]:
                        pkt_id = data[7]
                        if pkt_id in last_packets:
                            if last_packets[pkt_id] is None:
                                last_packets[pkt_id] = data
                                print(f"[INFO] Pacchetto {pkt_id:02x} inizializzato.")
                                continue
                            
                            # Confronta i byte e stampa solo quelli diversi
                            diffs = []
                            for i in range(len(data)):
                                if data[i] != last_packets[pkt_id][i]:
                                    # Escludiamo il checksum (byte 74) e i transienti F0/F7
                                    if i not in [0, 74, len(data)-1]:
                                        diffs.append(f"Byte {i}: {last_packets[pkt_id][i]} -> {data[i]} (0x{data[i]:02x})")
                            
                            if diffs:
                                print(f"\n--- CAMBIAMENTO NEL PACCHETTO {pkt_id:02x} ---")
                                for d in diffs:
                                    print(d)
                                last_packets[pkt_id] = data
    except KeyboardInterrupt:
        print("\nChiusura.")

if __name__ == "__main__":
    main()

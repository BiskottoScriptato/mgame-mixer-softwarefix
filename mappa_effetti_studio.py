import mido
import json
import time

EFFECT_NAMES = [
    "Monotone", "Lock Tune", "Pitch Correction", "Pitch Correct + Vibrato",
    "Sci Fi Villian", "Alien", "Robot 1", "Robot 2", "Robot 3", "Hi RPM",
    "Wobbley", "Tiny", "Male", "Female", "Child", "Ogre", "Squirrel",
    "Octave Up", "Octave Down", "High Fixed", "Low Fixed", "Unison",
    "Group 1", "Group 2", "Lock Tune 2", "Harmonies 1", "Harmonies 2",
    "Harmonies 3", "Smooth Harmonies", "Low Harmonies", "Bent Choir", "Deep Choir"
]

def main():
    print("=== M-GAME STUDIO EFFECT MAPPER ===")
    inputs = mido.get_input_names()
    nome = next((n for n in inputs if "M-Game" in n), None)
    
    if not nome:
        print("[ERRORE] Mixer non trovato tra i dispositivi MIDI.")
        return
        
    db = {}
    
    print(f"Sto per mappare {len(EFFECT_NAMES)} effetti.")
    print("ISTRUZIONI:")
    print("1. Apri il software ufficiale M-Game.")
    print("2. Io ti dirò quale effetto selezionare.")
    print("3. Tu lo selezioni nella tendina del software.")
    print("4. Lo script lo catturerà automaticamente e passerà al prossimo.")
    print("\nPremi INVIO per iniziare...")
    input()
    
    try:
        with mido.open_input(nome) as inport:
            for name in EFFECT_NAMES:
                print(f"\n--- [ AZIONE RICHIESTA ] ---")
                print(f"==> SELEZIONA ORA: '{name}' nel software M-Game")
                
                captured_packets = {}
                # Aspettiamo finché non catturiamo il pacchetto 0x00 (che indica il cambio effetto)
                while "00" not in captured_packets:
                    msg = inport.receive()
                    if msg and msg.type == 'sysex':
                        data = list(msg.bytes())
                        if len(data) >= 75 and data[1:6] == [0x00, 0x01, 0x05, 0x42, 0x00]:
                            pkt_id = f"{data[7]:02x}"
                            captured_packets[pkt_id] = data[1:-1]
                            if pkt_id == "00":
                                print(f"[OK] Catturato segnale per {name}!")
                
                # Catturiamo per un altro mezzo secondo per prendere gli altri pacchetti (10, 20, ecc.)
                start_time = time.time()
                while time.time() - start_time < 0.5:
                    msg = inport.poll()
                    if msg and msg.type == 'sysex':
                        data = list(msg.bytes())
                        if len(data) >= 75 and data[1:6] == [0x00, 0x01, 0x05, 0x42, 0x00]:
                            pkt_id = f"{data[7]:02x}"
                            captured_packets[pkt_id] = data[1:-1]
                    time.sleep(0.01)
                
                db[name] = captured_packets
                print(f"Salvataggio {name} completato ({len(captured_packets)} pacchetti registrati).")
    
        print("\n=== TUTTI GLI EFFETTI CATTURATI! ===")
        with open("vocal_db.json", "w") as f:
            json.dump(db, f, indent=4)
        
        print(f"File 'vocal_db.json' creato con successo ({len(db)} effetti).")
        print("Ora chiudi lo script e inviami il contenuto del file vocal_db.json!")
        
    except KeyboardInterrupt:
        print("\nChiusura.")

if __name__ == "__main__":
    main()

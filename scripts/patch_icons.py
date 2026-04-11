import re

icons = [
    ("game", 29, "Game (Controller)"),
    ("chat", 30, "Chat"),
    ("samp", 31, "Sampler"),
    ("sys", 32, "System")
]

def generate_icon_html(id_name, numeric_id, label):
    return f"""
        <div class="card">
            <label>Icona {label}</label>
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                <span style="color:#00e5ff; font-weight:bold;">Stato</span>
            </div>
            <select id="ico_{id_name}_mode" onchange="updateIconUI('{id_name}')" style="font-weight:bold; color:#ccc; margin-bottom:5px;">
                <option value="solid">Colore Fisso</option>
                <option value="pulse">Pulse (1-4 colori)</option>
                <option value="rainbow">Rainbow Animato</option>
            </select>
            <div id="ico_{id_name}_inputs" class="dynamic-box"></div>
            <button onclick="applyIcon('{id_name}', {numeric_id}, 'Icona {label}')" style="margin-top: 10px;">Applica a Icona {label}</button>
        </div>"""

with open('d:/Desktop/m-game/gui.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Pattern for replacing existing static icon cards
p_game = r'<div class="card">\s*<label>Icona Game \(Controller\)</label>.*?</button>\s*</div>'
p_chat = r'<div class="card">\s*<label>Icona Chat</label>.*?</button>\s*</div>'
p_samp = r'<div class="card">\s*<label>Icona Sampler</label>.*?</button>\s*</div>'
p_sys  = r'<div class="card">\s*<label>Icona System</label>.*?</button>\s*</div>'

text = re.sub(p_game, generate_icon_html("game", 29, "Game (Controller)"), text, flags=re.DOTALL)
text = re.sub(p_chat, generate_icon_html("chat", 30, "Chat"), text, flags=re.DOTALL)
text = re.sub(p_samp, generate_icon_html("samp", 31, "Sampler"), text, flags=re.DOTALL)
text = re.sub(p_sys,  generate_icon_html("sys", 32, "System"), text, flags=re.DOTALL)

with open('d:/Desktop/m-game/gui.html', 'w', encoding='utf-8') as f:
    f.write(text)

with open('d:/Desktop/m-game/index.html', 'r', encoding='utf-8') as f:
    js_text = f.read()

js_addition = """
        function updateIconUI(idName) {
            let mode = document.getElementById(`ico_${idName}_mode`).value;
            let container = document.getElementById(`ico_${idName}_inputs`);
            let prefix = `ico${idName}_`;
            
            let html = '';
            if (mode === 'solid') {
                html = `<input type="number" id="${prefix}c1" placeholder="Colore (0-127)">`;
            } else if (mode === 'pulse') {
                html = `<input type="text" id="${prefix}pcols" placeholder="Colori (Da 1 a 4 sep. virgola)">`;
            } else if (mode === 'rainbow') {
                html = `<select id="${prefix}lum"><option value="true">Lum. Alta</option><option value="false">Lum. Bassa</option></select>`;
            }
            container.innerHTML = html;
        }

        function _getIconParams(idName) {
            let mode = document.getElementById(`ico_${idName}_mode`).value;
            let prefix = `ico${idName}_`;
            let p1=0, p2=0, p3=0, p4=0;

            if (mode === 'solid') {
                p1 = val(`${prefix}c1`);
            } else if (mode === 'pulse') {
                let v = document.getElementById(`${prefix}pcols`) ? document.getElementById(`${prefix}pcols`).value : '';
                let arr = v.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n));
                p1 = arr[0] || 0; p2 = arr[1] || 0; p3 = arr[2] || 0; p4 = arr[3] || 0;
            } else if (mode === 'rainbow') {
                p1 = document.getElementById(`${prefix}lum`).value === 'true'; 
            }
            return { mode: mode, p1, p2, p3, p4 };
        }

        function applyIcon(idName, numericId, friendlyName) {
            let off = _getIconParams(idName);
            inv('imposta_tasto_mute_dinamico', [numericId, friendlyName, off.mode, off.p1, off.p2, off.p3, off.p4, 'solid', 0, 0, 0, 0]);
        }
"""
if "function updateIconUI" not in js_text:
    js_text = js_text.replace('function applyContent', js_addition + '\n        function applyContent')

# update onload
onload_patch = " updateIconUI('game'); updateIconUI('chat'); updateIconUI('samp'); updateIconUI('sys');"
if "updateIconUI('game')" not in js_text:
    js_text = re.sub(r'(updateContentUI\(\'off\'\);)(?!.*\bupdateIconUI\b)', r'\1' + onload_patch, js_text)

with open('d:/Desktop/m-game/index.html', 'w', encoding='utf-8') as f:
    f.write(js_text)

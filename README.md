# M-Game RGB Dual Dashboard - Global Support & Settings Panel.

An attempt to remake the M-Game RGB Dual mixer managing software (because the original sucks) by using a web ui, it provides software improvements and it solves (gets around) some driver issues. 
The main problem is that the driver used to comunicate with the mixer crashes when you try to close the bridge between your pc and the mixer, this means that if you accidentally close the m-game original software you can't re-open and you have to restart your pc;
We tried to fix it by creating a server that never closes the connection when you close the program (original) or the web ui.

## 🌟 Key Features
- 🔧 Fixed driver issue when closing and re-opening the official software.
- 🌐 Multi-Language UI
- ✨ LED Logic config
- 🎚️ Audio config

---

## 🚀 Installation & Setup

### 1. Prerequisites
Ensure you have **Python 3.10+** installed on your system.

### 2. Required Libraries
Install the mandatory dependencies using pip:
```bash
pip install flask flask-cors
```

### 3. Repository Structure
- `index.html`: The main web dashboard and translation engine.
- `gui.html`: The modular UI component file.
- `servermgame.py`: The Python backend handling hardware communication.
- `MGAME.py`: Core hardware protocol implementation.

---

## 🛠 Usage

1. **Start the Backend**:
   Run the Python server to establish communication with the M-Game hardware. (you can also compile it with pyinstaller and put it in shell:startup so it runs in the background).
   
   pyinstaller --onefile --noconsole servermgame.py
   ```bash
   python servermgame.py
   ```
2. **Open the Dashboard**:
   Open your preferred browser and navigate to the local server address (typically `http://127.0.0.1:5000` or the one specified in your terminal).

---

## 🤝 Contributing
Contributions, bug reports, and feature requests are welcome. Feel free to check the issues page or submit a pull request.

---

*Developed with passion for M-Game RGB Dual enthusiasts.*

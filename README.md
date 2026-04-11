# M-Game RGB Dual Dashboard - Global Support & Settings Panel

A comprehensive update to the M-Game RGB Dual mixer web interface, introducing persistent multi-language support (Italian/English), a modern settings management system, and refined UI/UX for absolute hardware control.

## 🌟 Key Features

- **🌐 Dynamic Internationalization (i18n)**: Seamlessly switch between Italian and English. The interface remembers your preference across sessions.
- **⚙️ New Settings Panel**: Access global configuration via a premium Glassmorphism-styled floating menu.
- **✨ Advanced LED Logic**:
  - Full control over active/inactive states for **Logo Audio**, **Mute Mic**, and **Censor** buttons.
  - Granular LED management for Side Strips (Left/Right), Voice FX, and Samples.
  - Integration for high/low luminosity modes in Rainbow effects.
- **🎹 Interactive Sampler**: Redesigned Sample cards with real-time state feedback (Empty, Unassigned, Playing).
- **🎚️ Integrated DSP Control**: Real-time management of Microphone EQ and Compressor settings.
- **🎨 Visual Refinement**: Optimized layout for 10-color gradients and improved spacing for hardware controls.

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
   Run the Python server to establish communication with the M-Game hardware.
   ```bash
   python servermgame.py
   ```
2. **Open the Dashboard**:
   Open your preferred browser and navigate to the local server address (typically `http://127.0.0.1:5000` or the one specified in your terminal).
3. **Customize Your Experience**:
   - Use the **Settings Icon** (bottom-right) to toggle between Italian and English.
   - Click "Apply" on any card to push changes directly to your M-Game RGB Dual hardware.

---

## 📂 Project Maintenance
This project includes a `.gitignore` to keep the repository clean from `__pycache__` and other temporary build artifacts.

---

## 🤝 Contributing
Contributions, bug reports, and feature requests are welcome. Feel free to check the issues page or submit a pull request.

---

*Developed with passion for M-Game RGB Dual enthusiasts.*

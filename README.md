# M-Game RGB Dual Dashboard - Global Support & Settings Panel

An attempt to remake the M-Game RGB Dual mixer managing software (because the original sucks) by using a web ui, it provides software improvements and it solves (gets around) some driver issues. 

## 🌟 Key Features

- **🌐 Multi-Language UI
- **✨ LED Logic config**:
  - Full control over leds configuration
- **🎚️ Audio config

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

---

## 🤝 Contributing
Contributions, bug reports, and feature requests are welcome. Feel free to check the issues page or submit a pull request.

---

*Developed with passion for M-Game RGB Dual enthusiasts.*

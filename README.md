# 🪄 Harry Potter OpenCV Games

<div align="center">

![Python](https://img.shields.io/badge/Python-3.7+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Google-FF6F00?style=for-the-badge&logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Real-time hand-tracking games with a Harry Potter twist — built for a college escape room expo.**

</div>

---

## 🎬 Demo

> Point your index finger at the camera and catch flying golden snitches in real time!

---

## 🎮 Features

- **Golden Snitch Chase** — Use your index finger to catch snitches flying across the screen
- **Real-time hand tracking** via MediaPipe — no controllers needed, just a webcam
- **Difficulty scaling** — snitches get faster as your score climbs
- **Combo system** — catch multiple snitches in quick succession for bonus points
- **Bludger obstacles** — avoid rogue bludgers or lose points
- **Power-ups** — special catches grant temporary abilities

---

## 🛠️ Tech Stack

| Library | Purpose |
|---|---|
| `opencv-python` | Video capture, rendering, frame processing |
| `mediapipe` | Real-time hand landmark detection |
| `numpy` | Coordinate math and array operations |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.7+
- A webcam
- Decent lighting (the hand tracker loves it)

### Installation

```bash
# Clone the repo
git clone https://github.com/Arvoxis/Harry-puttar-snitch-game.git
cd Harry-puttar-snitch-game

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
python snitch.py
```

---

## 🕹️ How to Play

1. Run the script — your webcam feed will open
2. **Point your index finger** toward the camera
3. Move your finger to **touch the golden snitch** on screen
4. Avoid bludgers — they deduct points
5. Build combos for multiplied scores!

**Controls:**
| Action | Gesture |
|---|---|
| Catch snitch | Point index finger at it |
| Quit game | Press `Q` |

---

## 📁 Project Structure

```
Harry-puttar-snitch-game/
├── snitch.py          # Main game loop
├── requirements.txt   # Python dependencies
├── README.md
└── .gitignore
```

---

## 🎓 Background

Built as part of a **Harry Potter themed escape room** at our college tech expo. The game was a crowd-pleaser — players had to catch 10 snitches within a time limit to unlock the next escape room clue.

---

## 📦 Requirements

```
opencv-python
mediapipe
numpy
```

---

## 🤝 Contributing

Pull requests are welcome! If you want to add a new game mode (Whomping Willow whacker, anyone?), fork the repo and open a PR.

---

## 📄 License

MIT License — free to use, remix, and build on.

---

<div align="center">
Made with ⚡ by <a href="https://github.com/Arvoxis">Arvoxis</a>
</div>

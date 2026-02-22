# Where Am I? – Ulauncher Extension

Quickly shows your location via IP (city, region, country, coordinates, IP).  
![demo gif](images/whereami.gif)

---

## Features

- 🌍 IP-based geolocation (multiple fallback APIs)
- 🏳️ Country flag (Unicode)
- 📋 One-click copy
- 🌐 Auto language (fallback: English)
- ⚡ Cached for 10 minutes
- 🔧 Custom keyword (`l` default)

---

## Installation

- Via Ulauncher → Extensions → Add:
  `https://github.com/elx4vier/whereami-ulauncher`

- Or clone into:
  `~/.local/share/ulauncher/extensions/`

---

## Usage

1. Open Ulauncher (`Ctrl+Space`)
2. Type `l`
3. Press Enter to copy result

---

## Config

Change keyword in:
Ulauncher → Preferences → Extensions

---

## How it works

- Uses: ip-api, freeipapi, ipapi, ipinfo
- First valid response is cached (10 min)
- Auto-detects system language

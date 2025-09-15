> **High-performance, real-time network monitoring and anomaly detection platform** — Capture live packets, track active flows, aggregate metrics, and detect statistical anomalies instantly.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://python.org)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite)](https://sqlite.org)
[![Tailwind](https://img.shields.io/badge/Styling-Tailwind_CSS-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)

---

## 🌟 Features
| Feature | Description |
|---|---|
| **Real-Time Packet Capture** | Captures live traffic natively using Scapy (`pcap`) or simulates high-volume traffic synthetically |
| **Dynamic Interface Swapping** | Swap the listening network interface instantly from the dashboard without restarting the server |
| **Flow Tracking** | Maintains state for active network flows (IP pairs, ports, protocols) to detect app-layer behavior |
| **Anomaly Detection Engine** | Uses Statistical Z-Score methodologies to detect irregular traffic patterns and volumetric spikes |
| **Live Traffic Dashboard** | Real-time WebSockets stream data to Recharts for beautiful bandwidth and protocol graphs |
| **Runtime Configuration** | Tweak anomaly sensitivity (Z-Score) and data retention dynamically from the UI settings |
| **Historical Analytics** | Analyze 1-second and 1-minute aggregated metrics across the network |
| **Modern UI/UX** | Sleek, bespoke vibrant light theme with responsive data tables and smooth glassmorphism |

---

## 🛠️ Technology Stack
| Component | Technology | Description |
|---|---|---|
| **Backend** | FastAPI + Python 3.10+ | High-performance async REST and WebSocket endpoints |
| **Database** | SQLite + SQLAlchemy | Async ORM for persistent storage of metrics and flows |
| **Packet Engine**| Scapy | Deep packet inspection and live network capture |
| **Frontend** | React + Vite | Blazing fast build tooling and modern frontend framework |
| **Styling** | Tailwind CSS | Utility-first framework used for the bespoke light theme |
| **Charts** | Recharts | Composable charting library for real-time graphs |

---

### Prerequisites
- Python 3.10+
- Node.js 18+
- Root/Sudo privileges (required for live `pcap` packet capture)

### 1. Clone & Configure
```bash
git clone https://github.com/NazeerSiddique-dev/NetWatch.git
cd NetWatch
cp .env.example .env
```

### 2. Start with Docker (Recommended)
```bash
docker-compose up -d
```
This starts the backend and serves the frontend on port 80.

### 3. Manual Setup (Backend)
```bash
# Install Python deps
cd backend
pip install -r requirements.txt

# Start backend (requires sudo for packet capture)
sudo python3 -m app.main
```

### 4. Manual Setup (Frontend)
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 📁 Project Structure
```text
NetWatch/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── core/                # Config, logging, security
│   ├── api/                 # REST & WebSocket API routers
│   │   ├── alerts.py        # Alert history
│   │   ├── flows.py         # Network flows
│   │   ├── interfaces.py    # System interfaces
│   │   ├── metrics.py       # Time-series stats
│   │   ├── settings.py      # Runtime configuration
│   │   └── websocket.py     # Real-time streams
│   ├── services/            # Core business logic
│   │   ├── collector/       # Pcap & Synthetic capture
│   │   ├── flow_processor/  # Tracking & Aggregation
│   │   ├── anomaly/         # Statistical Z-Score detection
│   │   └── monitoring/      # System health
│   ├── workers/             # Async background tasks
│   ├── models/              # SQLAlchemy database models
│   ├── db/                  # SQLite & Session management
│   └── requirements.txt
├── frontend/
│   ├── index.html           # HTML entry point
│   ├── vite.config.ts       # Vite config
│   ├── tailwind.config.js   # Bespoke light theme colors
│   ├── src/
│   │   ├── App.tsx          # React Router
│   │   ├── main.tsx         # React DOM mount
│   │   ├── context/         # WebSocket MetricsContext
│   │   ├── components/      # Reusable UI (MetricCard, TrafficChart)
│   │   ├── pages/           # Route views
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Analytics.tsx
│   │   │   ├── Interfaces.tsx
│   │   │   ├── Flows.tsx
│   │   │   └── Settings.tsx
│   │   └── index.css        # Global CSS
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🔐 Environment Variables
Copy `.env.example` to `.env` if you want to override default behavior:

```bash
# Collector Engine
COLLECTOR_MODE=pcap
DEFAULT_INTERFACE=wlp2s0

# Backend Config
BACKEND_PORT=8000
DEBUG=False
```

---

## 📊 API Documentation
After starting the backend, visit the auto-generated documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/interfaces` | List available network interfaces |
| `GET` | `/api/metrics/1s` | Historical 1-second metrics |
| `GET` | `/api/flows` | Active and historical flows |
| `GET` | `/api/alerts` | Anomaly alert history |
| `PATCH` | `/api/settings` | Update Z-Score or Interface dynamically |
| `WS` | `/ws/metrics` | Real-time traffic stream |
| `WS` | `/ws/alerts` | Real-time anomaly alerts stream |

---

## 📝 Git History Overview
- **Sep 15, 2025** - docs: Final tweaks, contrast optimizations, and project README
- **Sep 14, 2025** - feat: Add Docker containerization for deployment
- **Sep 12, 2025** - feat: Add dynamic runtime configuration settings
- **Sep 09, 2025** - feat: Implement Dashboard, Interfaces, and Flows pages
- **Sep 04, 2025** - feat: Build reusable UI components and Recharts integration
- **Sep 01, 2025** - feat: Add MetricsContext for WebSocket state management
- **Aug 28, 2025** - feat: Initialize React frontend with Tailwind CSS
- **Aug 25, 2025** - feat: Finalize FastAPI application and entrypoints
- **Aug 22, 2025** - feat: Implement REST API routes and WebSocket broadcast
- **Aug 19, 2025** - feat: Create background stream worker and alert service
- **Aug 14, 2025** - feat: Add statistical anomaly detection engine
- **Aug 08, 2025** - feat: Implement flow tracker and metric aggregator
- **Aug 03, 2025** - feat: Add packet collector and Scapy integration
- **Jul 29, 2025** - feat: Implement SQLAlchemy database models
- **Jul 25, 2025** - chore: Initial backend setup and configuration

---

## ⚠️ Disclaimer
NetWatch is a network monitoring tool designed for observability and analysis. Ensure you have proper authorization before capturing packets on external or shared networks.

---

*Built with FastAPI, React, Scapy, and ❤️*

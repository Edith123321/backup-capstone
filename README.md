#  HeartSound AI - RHD Detection System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Version](https://img.shields.io/badge/version-1.0.0-orange)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![React](https://img.shields.io/badge/react-18-cyan)

**An AI-driven IoT ecosystem designed to bridge the diagnostic gap for Rheumatic Heart Disease in low-resource African settings.**

---

##  Table of Contents
1. [Overview/Introduction](#1-overviewintroduction)
2. [Key Features](#2-key-features)
3. [System Architecture](#3-system-architecture)
4. [Machine Learning Model](#4-machine-learning-model)
5. [Installation & Setup](#5-installation--setup)
6. [Usage Guide](#6-usage-guide)
7. [API Documentation](#7-api-documentation)
8. [IoT Device Setup](#8-iot-device-setup)
9. [Contributing](#9-contributing)
10. [License](#10-license)
11. [Team & Acknowledgments](#11-team--acknowledgments)
12. [Additional Links](#12-additional-links)

---

## 1. Overview/Introduction

### The Problem: The "Silent Killer" in Africa
Rheumatic Heart Disease (RHD) remains a leading cause of preventable cardiac death among children and young adults in Sub-Saharan Africa. Stemming from untreated streptococcal throat infections, RHD leads to permanent valvular damage. Globally, it accounts for over 345,000 deaths annually. In regions like East Africa, the "Diagnostic Gap" is profound: specialized pediatric cardiologists are scarce, and the cost of gold-standard echocardiography equipment (ultrasound) is prohibitive for rural community clinics.

### Our Solution: HeartSound AI
**HeartSound AI** (Saka System) is a comprehensive diagnostic triage tool that decentralizes RHD screening. By combining low-cost IoT acoustic sensors with high-performance Machine Learning, we empower frontline healthcare workers to identify pathological heart murmurs before they progress to advanced heart failure. 

### Key Value Proposition
*   **High Accuracy:** Utilizing a Random Forest classifier achieving **98.4% accuracy**.
*   **Acoustic-First:** Unlike ultrasound, our system uses sound, requiring only a sub-$50 hardware investment.
*   **Rapid Triage:** The Jones Triage system provides immediate color-coded urgency levels to facilitate secondary prophylaxis with penicillin.
*   **Accessible:** Designed for offline capability and low-power mobile environments.

---

## 2. Key Features

*    **Single-Page Patient Encounter:** Streamlined UX allowing clinicians to register patient data, perform the Jones Triage survey, record live heart sounds, and receive an AI prediction—all without leaving the view.
*    **Comprehensive Patient Management:** A relational database system to create, search, and manage patient profiles with unique IDs.
*    **Jones Triage System:** An integrated digital version of the Jones Criteria, providing five color-coded urgency levels (Red, Orange, Yellow, Green, Blue) to guide clinical intervention.
*    **AI-Powered Diagnostics:** Real-time classification of Phonocardiogram (PCG) signals into severity grades (Normal, Borderline, Definite RHD).
*    **IoT Wireless Integration:** Seamless connection between the ESP32-powered digital stethoscope and the web dashboard via BLE/WebSockets.
*    **Longitudinal Care Tracking:** Automated history logs that track a patient’s disease progression, previous triage scores, and AI predictions over time.

---

## 3. System Architecture

### High-Level Diagram
```text
[ IoT Stethoscope ] --- BLE/WebSocket ---> [ React Frontend ]
       (ESP32)                               (Vite/MUI)
                                                 |
                                           HTTPS (REST)
                                                 |
                                         [ Flask Backend ]
                                                 |
        [ ML Model ] <--- Librosa <--- [ SQLite Database ]
      (Random Forest)
```

### Technology Stack Rationale
*   **Backend (Flask):** Chosen for its lightweight footprint and ease of integration with Python’s scientific stack (Librosa, Scikit-learn).
*   **Frontend (React + Vite):** Provides a highly responsive Single Page Application (SPA) experience. Material-UI (MUI) ensures a professional, calming clinical aesthetic.
*   **Database (SQLite):** Used for its serverless nature, allowing the entire system to be deployed on local hospital workstations without complex DB administration.
*   **Authentication (Google OAuth 2.0):** Ensures secure access for healthcare providers while leveraging existing institutional credentials.
*   **Hardware (ESP32):** Selected for its built-in Bluetooth/WiFi capabilities and I2S support, critical for high-fidelity digital audio capture.

---

## 4. Machine Learning Model

### Dataset & Preprocessing
The model was trained on a balanced hybrid dataset consisting of over 8,000 clinical recordings (PhysioNet & CirCOR Digiscope). 
1.  **Noise Mitigation:** A 5th-order Butterworth Bandpass filter (20Hz - 400Hz) is applied to isolate valvular murmurs from ambient environmental noise.
2.  **Feature Extraction:** 1D audio signals are transformed into 2D Mel Spectrograms. We extract 40 Mel-frequency cepstral coefficients (MFCCs) to represent the "texture" of the murmur.

### Architecture & Performance
*   **Model:** Random Forest Classifier (n_estimators=100).
*   **Rationale:** Random Forest proved superior in handling the high-dimensional feature vectors extracted from audio, offering better generalizability than standard CNNs in low-data medical scenarios.
*   **Metrics:**
    *   **Accuracy:** 98.4%
    *   **Area Under Curve (AUC):** 0.9995
    *   **Precision/Recall:** Optimized for high sensitivity to ensure zero "False Negatives" for severe RHD.

### Validation Strategy
We implemented a **Patient-Level Split**. This ensures that segments from the same patient are never shared between the training and testing sets, preventing "data leakage" and ensuring the model works on entirely new individuals.

---

## 5. Installation & Setup

### Prerequisites
- **Python:** 3.12+
- **Node.js:** 18.x+ (LTS)
- **C++ Build Tools:** (For Librosa/Numpy compilation)

### Backend Installation
```bash
# Navigate to backend directory
cd capstone/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from services.database import init_db; init_db()"
```

### Frontend Installation
```bash
# Navigate to frontend directory
cd capstone/frontend_web

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## 6. Usage Guide

### Standard Clinical Workflow
1.  **Login:** Healthcare provider authenticates via Google OAuth.
2.  **Dashboard:** Navigate to "New Encounter."
3.  **Patient Info:** Input name, age, and location. If the patient exists, search and link the profile.
4.  **Jones Triage:** Complete the 5-point checklist. The system calculates the urgency color code instantly.
5.  **Record Sound:** Place the IoT Stethoscope on the **Mitral Valve** location. Click "Record" on the dashboard.
6.  **AI Result:** The dashboard displays "Normal," "Borderline," or "Definite RHD" with a confidence score.
7.  **History:** Click "Save Encounter" to log the data for future longitudinal tracking.

---

## 7. API Documentation

### Authentication
`POST /api/v1/auth/google`
- **Description:** Exchange Google Token for internal JWT.
- **Payload:** `{ "token": "..." }`

### Screening
`POST /api/v1/screening/predict`
- **Description:** Upload audio for AI classification.
- **Payload:** Multipart Form-data (audio file).
- **Response:**
  ```json
  {
    "grade": "Definite RHD",
    "confidence": 0.98,
    "recommendation": "Immediate Referral Required"
  }
  ```

---

## 8. IoT Device Setup

### Components
- ESP32 Development Board (WROOM-32)
- INMP441 I2S MEMS Microphone
- 3.7V LiPo Battery
- 3D Printed Acoustic Chamber

### Wiring Guide
| INMP441 | ESP32 Pin |
| :--- | :--- |
| VDD | 3.3V |
| GND | GND |
| SD | GPIO 32 |
| WS | GPIO 25 |
| SCK | GPIO 33 |

### Firmware Upload
1.  Open `iot/src/main.ino` in Arduino IDE.
2.  Install `ESP32` board support and `WebSocketsServer` library.
3.  Configure your WiFi SSID/Password in `Config.h`.
4.  Upload to the ESP32 board.

---

## 9. Contributing

We welcome contributions from the Global Health and Med-Tech community.
1.  **Fork** the repository.
2.  Create a **Feature Branch** (`git checkout -b feature/AmazingFeature`).
3.  **Commit** your changes (`git commit -m 'Add some AmazingFeature'`).
4.  **Push** to the branch (`git push origin feature/AmazingFeature`).
5.  Open a **Pull Request**.

---

## 10. License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## 11. Team & Acknowledgments

*   **Lead Researcher:** Edith Nyanjiru Githinji
*   **Supervisors:** Dirac Murairi
*   **Institutional Support:** African Leadership University (ALU)
*   **Special Thanks:** To the researchers at PhysioNet and CirCOR for providing the foundational datasets that made this AI training possible.

---

## 12. Additional Links

*    [Technical Walkthrough Video](https://canva.link/r39gcls1lkub60j)
*    [Live Demo Link](https://backup-capstone-mbq6.onrender.com)
*    [Full Research Proposal](docs/proposal.pdf)
*    [WandB Training Dashboard](https://wandb.ai/placeholder)

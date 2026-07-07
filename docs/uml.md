# SAKA RHD System — UML Suite

Standardized UML diagrams for the SAKA (HeartSound AI) RHD screening platform.
All diagrams are derived directly from the implemented codebase (Flask backend,
SQLite schema in `backend/services/database.py`, and the React dashboard) and
render natively on GitHub via Mermaid.

> For high-resolution raster/vector exports, paste any block into
> [mermaid.live](https://mermaid.live) and export PNG/SVG.

---

## 1. Use Case Diagram

```mermaid
flowchart TB
    doctor([Healthcare Provider / Doctor])
    device([IoT Stethoscope - ESP32])
    cardio([Cardiologist])

    subgraph SAKA["SAKA RHD Platform"]
        UC1((Authenticate via Google OAuth))
        UC2((Register / Search Patient))
        UC3((Perform Jones Triage))
        UC4((Record Heart Sound))
        UC5((Run AI RHD Screening))
        UC6((View Severity Grade))
        UC7((View Prognostic Risk - Markov))
        UC8((Generate PDF Referral))
        UC9((View Longitudinal History))
    end

    doctor --> UC1
    doctor --> UC2
    doctor --> UC3
    doctor --> UC4
    doctor --> UC9
    device --> UC4
    UC4 --> UC5
    UC5 --> UC6
    UC6 --> UC7
    UC7 --> UC8
    UC8 --> cardio
```

---

## 2. Entity-Relationship Diagram (ERD)

Reflects the exact SQLite schema created in `backend/services/database.py`.

```mermaid
erDiagram
    DOCTORS ||--o{ PATIENTS : manages
    DOCTORS ||--o{ TRIAGE_RECORDS : records
    DOCTORS ||--o{ HEART_SOUND_RECORDINGS : records
    DOCTORS ||--o{ IOT_DEVICES : owns
    PATIENTS ||--o{ TRIAGE_RECORDS : has
    PATIENTS ||--o{ HEART_SOUND_RECORDINGS : has
    PATIENTS ||--o{ SEVERITY_HISTORY : has
    PATIENTS ||--o{ FOLLOW_UP_REMINDERS : has
    HEART_SOUND_RECORDINGS ||--o{ SEVERITY_HISTORY : produces

    DOCTORS {
        text id PK
        text email UK
        text name
        text specialty
        text hospital
        timestamp created_at
        timestamp last_login
    }
    PATIENTS {
        text id PK
        text doctor_id FK
        text name
        int age
        text gender
        text contact
        text medical_history
        text rhd_status
        text rhd_diagnosis_date
        timestamp created_at
    }
    TRIAGE_RECORDS {
        text id PK
        text patient_id FK
        text doctor_id FK
        text triage_level
        text triage_color
        int triage_score
        real heart_rate
        real oxygen_saturation
        text symptoms
        timestamp created_at
    }
    HEART_SOUND_RECORDINGS {
        text id PK
        text patient_id FK
        text doctor_id FK
        text file_path
        text prediction
        real confidence
        int severity_grade
        text severity_label
        text auscultation_point
        real rhd_risk_score
        timestamp recorded_at
    }
    SEVERITY_HISTORY {
        text id PK
        text patient_id FK
        text recording_id FK
        int severity_grade
        text severity_label
        text prediction
        real confidence
        timestamp assessed_at
    }
    IOT_DEVICES {
        text id PK
        text doctor_id FK
        text device_name
        text ip_address
        text mac_address
        text status
        timestamp last_connected
    }
    FOLLOW_UP_REMINDERS {
        text id PK
        text patient_id FK
        int recommended_days
        text reason
        boolean completed
        timestamp created_at
    }
```

---

## 3. Class Diagram (Backend Services)

Reflects the implemented service layer in `backend/services/` and
`backend/api/v1/screening/`.

```mermaid
classDiagram
    class HeartSoundClassifier {
        +model
        +scaler
        +predict(filepath) dict
    }
    class FeatureExtractor {
        <<module: feature_extraction>>
        +extract_feature_vector(signal, sr) ndarray
        -_stft_mag()
        -_mfcc()
        -_mel_filterbank()
        -_zero_crossing_rate()
    }
    class SeverityGrader {
        +grade_from_prediction(prediction, confidence, point) SeverityResult
        +get_severity_history(patient_id) list
        +get_severity_trend(patient_id) dict
    }
    class SeverityResult {
        +int grade
        +str label
        +str color
        +float confidence
        +to_dict() dict
    }
    class MarkovModel {
        +transition_matrix(treatment) ndarray
        +project(grade, months) ndarray
        +steady_state() ndarray
    }
    class RiskCalculator {
        +calculate_risk(patient_id, clinical_data) dict
        +get_longitudinal_prediction(patient_id, months) dict
    }
    class ReportGenerator {
        +generate(patient_id, report_data) dict
        -_generate_waveform_image()
    }
    class Database {
        +save_heart_sound_recording()
        +get_recordings_by_patient()
        +get_severity_history()
        +get_severity_trend()
    }

    HeartSoundClassifier ..> FeatureExtractor : uses
    SeverityGrader ..> SeverityResult : produces
    SeverityGrader ..> Database : reads/writes
    RiskCalculator ..> MarkovModel : uses
    RiskCalculator ..> Database : reads
    ReportGenerator ..> Database : reads
    ReportGenerator ..> RiskCalculator : reads risk
    ReportGenerator ..> SeverityGrader : reads severity
```

---

## 4. Sequence Diagram — Screening Encounter

The end-to-end flow implemented across the IoT firmware, React dashboard, Flask
API (`/api/v1/screening/predict`), and the service layer.

```mermaid
sequenceDiagram
    actor Doctor
    participant Steth as IoT Stethoscope (ESP32)
    participant UI as React Dashboard
    participant API as Flask API
    participant CLF as HeartSoundClassifier
    participant FE as FeatureExtractor
    participant SG as SeverityGrader
    participant DB as SQLite DB

    Doctor->>UI: Start new encounter (patient + Jones triage)
    Doctor->>Steth: Place on mitral valve, record
    Steth-->>UI: Stream PCG audio (BLE / WebSocket)
    UI->>API: POST /screening/predict (WAV + patient_id)
    API->>CLF: predict(wav)
    CLF->>FE: extract_feature_vector(signal)
    FE-->>CLF: 51-feature vector (numba-safe)
    CLF-->>API: {class, confidence, prob}
    API->>SG: grade_from_prediction(class, confidence, point)
    SG-->>API: SeverityResult (grade 0/1/2, color)
    API->>DB: save recording + severity_history
    API-->>UI: {prediction, confidence, severity}
    UI-->>Doctor: Display grade + recommendation
    opt Referral needed
        Doctor->>API: POST /reports/generate
        API-->>Doctor: Color-coded PDF referral
    end
```

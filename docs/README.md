# SAKA RHD — Technical Documentation

Documentation package for the SAKA (HeartSound AI) RHD screening capstone.

## Contents (in this repo)
| Document | Description |
|----------|-------------|
| [technical_specification.md](technical_specification.md) | System architecture + the Numba-safe DSP/feature pipeline |
| [uml.md](uml.md) | UML suite — Use Case, ERD, Class, and Sequence diagrams (Mermaid) |
| [clinical_evaluation_report.md](clinical_evaluation_report.md) | Confusion matrix, F1, AUC-ROC from the trained model artifacts |

## Related artifacts elsewhere in the repo
- Model metrics & plots: `ai_model/models/mitral_classifier_v4/` (`model_comparison.csv`, `confusion_matrix_*.png`, `roc_curves.png`)
- Bill of Materials: `iot/schematic/components_list.csv`
- Firmware: `iot/src/` (ESP32 / PlatformIO)
- Feature pipeline: `backend/api/v1/screening/feature_extraction.py`

## Author-supplied deliverables (not generated here)
These are the researcher's academic IP / human-subjects records and must be
authored and added directly:
- **Final Research Thesis** (5-chapter report)
- **Ethical Compliance Dossier** — Integrated Ethics & Risk Assessment forms and
  signed Parent/Guardian consent forms from the Gisozi pilot
- High-resolution rendered CAD (`.stl`) and schematic exports (require CAD tools)

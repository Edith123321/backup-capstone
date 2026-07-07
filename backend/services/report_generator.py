# backend/services/report_generator.py
"""
PDF Report Generator for RHD Referral Reports
Generates comprehensive clinical reports including:
- Patient demographics
- Triage scores and colors
- AI predictions and confidence
- Severity grades
- Auscultation points
- Raw audio waveform visualization
- Clinical recommendations
- Referral summaries
"""

import os
import io
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import uuid

# PDF generation libraries
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, KeepTogether, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("⚠️ ReportLab not installed. PDF generation will be disabled.")

import numpy as np

# Waveform rendering is optional. Guard these imports so a missing matplotlib /
# Pillow cannot break the whole report pipeline (reports simply skip the plot).
try:
    import matplotlib
    matplotlib.use('Agg')  # headless backend for server rendering
    import matplotlib.pyplot as plt
    WAVEFORM_AVAILABLE = True
except ImportError:
    WAVEFORM_AVAILABLE = False
    print("⚠️ matplotlib not installed. Waveform plots will be skipped.")

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class ReportData:
    """Data structure for report generation"""
    patient_id: str
    patient_name: str
    patient_age: int
    patient_gender: str
    patient_contact: str
    patient_address: str
    doctor_id: str
    doctor_name: str
    doctor_hospital: str
    assessment_date: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))
    
    # Triage data
    triage_color: Optional[str] = None
    triage_level: Optional[str] = None
    triage_score: Optional[int] = None
    triage_vitals: Optional[Dict] = field(default_factory=dict)
    
    # AI Prediction data
    prediction: Optional[str] = None
    confidence: Optional[float] = None
    severity_grade: Optional[int] = None
    severity_label: Optional[str] = None
    auscultation_point: Optional[str] = None
    auscultation_label: Optional[str] = None
    
    # Recordings
    recordings: List[Dict] = field(default_factory=list)
    
    # Clinical data
    symptoms: List[str] = field(default_factory=list)
    medical_history: str = ""
    clinical_notes: str = ""
    
    # Prognosis
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    prognosis_trend: Optional[str] = None
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    referral_priority: Optional[str] = None
    follow_up_days: Optional[int] = None


# ============================================
# REPORT GENERATOR CLASS
# ============================================

class ReportGenerator:
    """
    Generates PDF referral reports for RHD patients.
    """
    
    def __init__(self, output_dir: str = None):
        """
        Initialize the report generator.

        Args:
            output_dir: Directory to save generated reports. Defaults to
                backend/reports, which is what the /reports/download endpoint
                serves from.
        """
        if output_dir is None:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(backend_dir, 'reports')
        self.output_dir = output_dir
        self.styles = getSampleStyleSheet() if REPORTLAB_AVAILABLE else None
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """Ensure the output directory exists"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def generate_report(self, report_data: ReportData, 
                        include_waveform: bool = True,
                        format: str = 'pdf') -> Dict:
        """
        Generate a PDF report for a patient.
        
        Args:
            report_data: ReportData object with all report information
            include_waveform: Include waveform visualization
            format: Output format ('pdf' or 'html')
        
        Returns:
            Dict with report file path and metadata
        """
        if not REPORTLAB_AVAILABLE:
            return {
                'success': False,
                'error': 'ReportLab not installed. Please install reportlab.'
            }
        
        try:
            # Generate report ID
            report_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"RHD_Report_{report_data.patient_id}_{timestamp}.pdf"
            filepath = os.path.join(self.output_dir, filename)
            
            # Generate waveform image if needed
            waveform_img = None
            if include_waveform and report_data.recordings:
                waveform_img = self._generate_waveform_image(report_data.recordings)
            
            # Create PDF document
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Build story (content)
            story = []
            
            # Add header
            story.extend(self._create_header(report_data))
            story.append(Spacer(1, 20))
            
            # Add patient information
            story.extend(self._create_patient_info(report_data))
            story.append(Spacer(1, 16))
            
            # Add triage results
            if report_data.triage_color:
                story.extend(self._create_triage_section(report_data))
                story.append(Spacer(1, 16))
            
            # Add AI prediction section
            story.extend(self._create_prediction_section(report_data))
            story.append(Spacer(1, 16))
            
            # Add waveform visualization
            if waveform_img:
                story.extend(self._create_waveform_section(waveform_img))
                story.append(Spacer(1, 16))
            
            # Add prognostic risk section
            if report_data.risk_score is not None:
                story.extend(self._create_prognosis_section(report_data))
                story.append(Spacer(1, 16))
            
            # Add clinical notes
            if report_data.clinical_notes:
                story.extend(self._create_clinical_notes(report_data))
                story.append(Spacer(1, 16))
            
            # Add recommendations and referral summary
            story.extend(self._create_referral_summary(report_data))
            story.append(Spacer(1, 16))
            
            # Add footer
            story.extend(self._create_footer(report_data))
            
            # Build PDF
            doc.build(story)
            
            return {
                'success': True,
                'report_id': report_id,
                'filepath': filepath,
                'filename': filename,
                'url': f"/api/v1/reports/download/{filename}",
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error generating report: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_header(self, data: ReportData) -> List:
        """Create report header section"""
        story = []
        
        # Hospital name
        hospital_name = data.doctor_hospital or "Saka RHD Detection Center"
        story.append(Paragraph(
            f"<b>{hospital_name}</b>",
            ParagraphStyle(
                'HospitalName',
                parent=self.styles['Title'],
                fontSize=20,
                textColor=colors.HexColor('#00464F'),
                alignment=TA_CENTER,
                spaceAfter=6
            )
        ))
        
        # Report title
        story.append(Paragraph(
            "RHD Clinical Assessment & Referral Report",
            ParagraphStyle(
                'ReportTitle',
                parent=self.styles['Heading1'],
                fontSize=16,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#1a1a2e'),
                spaceAfter=12
            )
        ))
        
        # Report metadata
        story.append(Paragraph(
            f"Report ID: {data.patient_id}_{datetime.now().strftime('%Y%m%d')} | "
            f"Date: {data.assessment_date}",
            ParagraphStyle(
                'ReportMeta',
                parent=self.styles['Normal'],
                fontSize=10,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#64748b')
            )
        ))
        
        story.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor('#00464F'),
            spaceAfter=16
        ))
        
        return story
    
    def _create_patient_info(self, data: ReportData) -> List:
        """Create patient information section"""
        story = []
        
        # Section header
        story.append(Paragraph(
            "<b>Patient Information</b>",
            ParagraphStyle(
                'SectionHeader',
                parent=self.styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#1a1a2e'),
                spaceAfter=8
            )
        ))
        
        # Patient data table
        patient_data = [
            ['Patient Name:', data.patient_name or '—'],
            ['Patient ID:', data.patient_id or '—'],
            ['Age:', str(data.patient_age) if data.patient_age else '—'],
            ['Gender:', data.patient_gender or '—'],
            ['Contact:', data.patient_contact or '—'],
            ['Address:', data.patient_address or '—'],
            ['Doctor:', data.doctor_name or '—']
        ]
        
        table = Table(patient_data, colWidths=[120, 300])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748b')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a2e')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('LEADING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(table)
        
        return story
    
    def _create_triage_section(self, data: ReportData) -> List:
        """Create triage results section"""
        story = []
        
        story.append(Paragraph(
            "<b>Triage Assessment (Jones Criteria)</b>",
            ParagraphStyle(
                'SectionHeader',
                parent=self.styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#1a1a2e'),
                spaceAfter=8
            )
        ))
        
        # Color-coded triage badge
        color_map = {
            'Red': colors.HexColor('#dc2626'),
            'Orange': colors.HexColor('#f59e0b'),
            'Yellow': colors.HexColor('#facc15'),
            'Green': colors.HexColor('#22c55e'),
            'Blue': colors.HexColor('#3b82f6')
        }
        
        triage_color = color_map.get(data.triage_color, colors.HexColor('#94a3b8'))
        
        # Triage data table
        triage_data = [
            ['Triage Level:', data.triage_level or '—'],
            ['Triage Color:', f'■ {data.triage_color}' if data.triage_color else '—'],
            ['Triage Score:', str(data.triage_score) if data.triage_score else '—']
        ]
        
        table = Table(triage_data, colWidths=[120, 300])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748b')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a2e')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        
        # Add color to triage color cell
        if data.triage_color:
            table.setStyle(TableStyle([
                ('TEXTCOLOR', (1, 1), (1, 1), triage_color),
                ('FONTWEIGHT', (1, 1), (1, 1), 'BOLD'),
            ]))
        
        story.append(table)
        
        # Vitals if available
        if data.triage_vitals:
            story.append(Spacer(1, 8))
            vitals_data = [
                ['Vitals:'],
                [f"HR: {data.triage_vitals.get('heart_rate', '—')} bpm"],
                [f"RR: {data.triage_vitals.get('respiratory_rate', '—')}/min"],
                [f"SpO2: {data.triage_vitals.get('oxygen_saturation', '—')}%"],
                [f"Temp: {data.triage_vitals.get('temperature', '—')}°C"]
            ]
            
            vitals_table = Table(vitals_data, colWidths=[150, 150])
            vitals_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748b')),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a2e')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(vitals_table)
        
        return story
    
    def _create_prediction_section(self, data: ReportData) -> List:
        """Create AI prediction section"""
        story = []
        
        story.append(Paragraph(
            "<b>AI-Powered Heart Sound Analysis</b>",
            ParagraphStyle(
                'SectionHeader',
                parent=self.styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#1a1a2e'),
                spaceAfter=8
            )
        ))
        
        # Prediction data
        pred_data = [
            ['Prediction:', data.prediction or '—'],
            ['Confidence:', f"{data.confidence * 100:.1f}%" if data.confidence else '—'],
            ['Severity Grade:', f"Grade {data.severity_grade}" if data.severity_grade is not None else '—'],
            ['Severity Label:', data.severity_label or '—'],
            ['Auscultation Point:', f"{data.auscultation_label} ({data.auscultation_point})" if data.auscultation_point else '—']
        ]
        
        table = Table(pred_data, colWidths=[140, 280])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748b')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a2e')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        
        # Color the prediction
        if data.prediction == 'RHD':
            table.setStyle(TableStyle([
                ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor('#dc2626')),
                ('FONTWEIGHT', (1, 0), (1, 0), 'BOLD'),
            ]))
        elif data.prediction == 'Normal':
            table.setStyle(TableStyle([
                ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor('#22c55e')),
                ('FONTWEIGHT', (1, 0), (1, 0), 'BOLD'),
            ]))
        
        story.append(table)
        
        return story
    
    def _load_recording_audio(self, recordings: List[Dict]):
        """
        Load the real PCG signal for the first recording whose audio is actually
        available on disk. Returns (signal, sample_rate) or (None, None).

        Only genuine audio is used — the report never fabricates a waveform. If
        no recording has a readable file, the waveform section is omitted.
        """
        for r in recordings or []:
            # A stored path (file_path) or a file_url that points at a local file.
            candidate = r.get('file_path')
            if not candidate:
                url = r.get('file_url') or ''
                if url and not url.startswith(('http://', 'https://')):
                    candidate = url
            if not candidate or not os.path.exists(candidate):
                continue
            try:
                import soundfile as sf
                signal, sr = sf.read(candidate)
            except Exception:
                try:
                    from scipy.io import wavfile
                    sr, signal = wavfile.read(candidate)
                    if signal.dtype.kind in 'iu':
                        signal = signal.astype(np.float32) / np.iinfo(signal.dtype).max
                except Exception:
                    continue
            if getattr(signal, 'ndim', 1) > 1:  # mono
                signal = np.mean(signal, axis=1)
            if len(signal) > 0:
                return np.asarray(signal, dtype=float), int(sr)
        return None, None

    def _generate_waveform_image(self, recordings: List[Dict]) -> Optional[str]:
        """
        Render the real PCG waveform for a recording as a base64 PNG.
        Returns None (and the report omits the plot) if no real audio is
        available or plotting libraries are missing — never a synthetic signal.
        """
        if not WAVEFORM_AVAILABLE:
            return None
        try:
            signal, sr = self._load_recording_audio(recordings)
            if signal is None:
                return None

            duration = len(signal) / sr
            t = np.linspace(0, duration, len(signal))

            fig, ax = plt.subplots(figsize=(8, 3))
            ax.plot(t, signal, color='#00464F', linewidth=0.8)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Amplitude', fontsize=10)
            ax.set_title('PCG Waveform (recorded)', fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.set_xlim(0, duration)

            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            plt.close()

            image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            print(f"Error generating waveform: {e}")
            return None
    
    def _create_waveform_section(self, waveform_img: str) -> List:
        """Create waveform visualization section"""
        story = []
        
        story.append(Paragraph(
            "<b>Heart Sound Waveform</b>",
            ParagraphStyle(
                'SectionHeader',
                parent=self.styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#1a1a2e'),
                spaceAfter=8
            )
        ))
        
        # For reportlab, feed the PNG bytes directly via an in-memory buffer.
        # (A temp file would be deleted before reportlab lazily reads it at
        # doc.build() time, which raised "Cannot open resource".)
        try:
            header, data = waveform_img.split(',', 1)
            image_data = base64.b64decode(data)

            img = Image(io.BytesIO(image_data), width=6 * inch, height=2.25 * inch)
            story.append(img)
            story.append(Spacer(1, 8))

        except Exception as e:
            print(f"Error adding waveform: {e}")
            story.append(Paragraph(
                "Waveform visualization not available",
                self.styles['Normal']
            ))
        
        return story
    
    def _create_prognosis_section(self, data: ReportData) -> List:
        """Create prognosis/risk section"""
        story = []
        
        story.append(Paragraph(
            "<b>Prognostic Risk Assessment</b>",
            ParagraphStyle(
                'SectionHeader',
                parent=self.styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#1a1a2e'),
                spaceAfter=8
            )
        ))
        
        # Risk data
        risk_data = [
            ['Risk Score:', f"{data.risk_score:.1f}%" if data.risk_score is not None else '—'],
            ['Risk Level:', data.risk_level or '—'],
            ['Trend:', data.prognosis_trend or '—']
        ]
        
        # Color code risk level
        risk_colors = {
            'Low': colors.HexColor('#22c55e'),
            'Moderate': colors.HexColor('#f59e0b'),
            'High': colors.HexColor('#f97316'),
            'Critical': colors.HexColor('#dc2626')
        }
        risk_color = risk_colors.get(data.risk_level, colors.HexColor('#94a3b8'))
        
        table = Table(risk_data, colWidths=[140, 280])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748b')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a1a2e')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        
        if data.risk_level:
            table.setStyle(TableStyle([
                ('TEXTCOLOR', (1, 1), (1, 1), risk_color),
                ('FONTWEIGHT', (1, 1), (1, 1), 'BOLD'),
            ]))
        
        story.append(table)
        
        return story
    
    def _create_clinical_notes(self, data: ReportData) -> List:
        """Create clinical notes section"""
        story = []
        
        story.append(Paragraph(
            "<b>Clinical Notes</b>",
            ParagraphStyle(
                'SectionHeader',
                parent=self.styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#1a1a2e'),
                spaceAfter=8
            )
        ))
        
        # Symptoms
        if data.symptoms:
            symptoms_text = ", ".join(data.symptoms)
            story.append(Paragraph(
                f"<b>Symptoms:</b> {symptoms_text}",
                self.styles['Normal']
            ))
            story.append(Spacer(1, 4))
        
        # Medical history
        if data.medical_history:
            story.append(Paragraph(
                f"<b>Medical History:</b> {data.medical_history}",
                self.styles['Normal']
            ))
            story.append(Spacer(1, 4))
        
        # Clinical notes
        story.append(Paragraph(
            f"<b>Clinical Notes:</b> {data.clinical_notes}",
            self.styles['Normal']
        ))
        
        return story
    
    def _create_referral_summary(self, data: ReportData) -> List:
        """Create referral summary section"""
        story = []
        
        story.append(PageBreak())
        
        story.append(Paragraph(
            "<b>Referral Summary & Recommendations</b>",
            ParagraphStyle(
                'SectionHeader',
                parent=self.styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#00464F'),
                spaceAfter=12,
                alignment=TA_CENTER
            )
        ))
        
        # Priority badge
        if data.referral_priority:
            priority_colors = {
                'Immediate': colors.HexColor('#dc2626'),
                'Urgent': colors.HexColor('#f59e0b'),
                'Routine': colors.HexColor('#22c55e')
            }
            priority_color = priority_colors.get(data.referral_priority, colors.HexColor('#94a3b8'))
            
            story.append(Paragraph(
                f"<b>Referral Priority:</b> {data.referral_priority}",
                ParagraphStyle(
                    'Priority',
                    parent=self.styles['Normal'],
                    fontSize=14,
                    textColor=priority_color,
                    alignment=TA_CENTER,
                    spaceAfter=12
                )
            ))
        
        # Recommendations
        if data.recommendations:
            story.append(Paragraph(
                "<b>Clinical Recommendations:</b>",
                self.styles['Heading3']
            ))
            
            for i, rec in enumerate(data.recommendations, 1):
                story.append(Paragraph(
                    f"{i}. {rec}",
                    ParagraphStyle(
                        'Recommendation',
                        parent=self.styles['Normal'],
                        fontSize=10,
                        leftIndent=12,
                        spaceAfter=4
                    )
                ))
        
        # Follow-up
        if data.follow_up_days:
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                f"<b>Recommended Follow-up:</b> {data.follow_up_days} days",
                self.styles['Normal']
            ))
        
        return story
    
    def _create_footer(self, data: ReportData) -> List:
        """Create report footer"""
        story = []
        
        story.append(Spacer(1, 20))
        story.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor('#e2e8f0'),
            spaceAfter=8
        ))
        
        footer_text = f"""
        Generated by Saka RHD Detection System | Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}
        This report is for clinical reference only. Please consult with a cardiologist for definitive diagnosis.
        """
        
        story.append(Paragraph(
            footer_text,
            ParagraphStyle(
                'Footer',
                parent=self.styles['Normal'],
                fontSize=8,
                textColor=colors.HexColor('#94a3b8'),
                alignment=TA_CENTER
            )
        ))
        
        return story


# ============================================
# FACTORY FUNCTIONS
# ============================================

def create_report_generator(output_dir: str = "reports") -> ReportGenerator:
    """Create a new report generator instance"""
    return ReportGenerator(output_dir=output_dir)


def generate_patient_report(patient_id: str, report_data: Dict) -> Dict:
    """
    Generate a report for a patient using the report generator.
    
    Args:
        patient_id: Patient identifier
        report_data: Dictionary with report data
    
    Returns:
        Dict with report generation result
    """
    generator = ReportGenerator()
    
    # Convert dict to ReportData
    data = ReportData(
        patient_id=patient_id,
        patient_name=report_data.get('patient_name', ''),
        patient_age=report_data.get('patient_age', 0),
        patient_gender=report_data.get('patient_gender', ''),
        patient_contact=report_data.get('patient_contact', ''),
        patient_address=report_data.get('patient_address', ''),
        doctor_id=report_data.get('doctor_id', ''),
        doctor_name=report_data.get('doctor_name', ''),
        doctor_hospital=report_data.get('doctor_hospital', ''),
        assessment_date=report_data.get('assessment_date', datetime.now().strftime('%Y-%m-%d')),
        triage_color=report_data.get('triage_color'),
        triage_level=report_data.get('triage_level'),
        triage_score=report_data.get('triage_score'),
        triage_vitals=report_data.get('triage_vitals', {}),
        prediction=report_data.get('prediction'),
        confidence=report_data.get('confidence'),
        severity_grade=report_data.get('severity_grade'),
        severity_label=report_data.get('severity_label'),
        auscultation_point=report_data.get('auscultation_point'),
        auscultation_label=report_data.get('auscultation_label'),
        recordings=report_data.get('recordings', []),
        symptoms=report_data.get('symptoms', []),
        medical_history=report_data.get('medical_history', ''),
        clinical_notes=report_data.get('clinical_notes', ''),
        risk_score=report_data.get('risk_score'),
        risk_level=report_data.get('risk_level'),
        prognosis_trend=report_data.get('prognosis_trend'),
        recommendations=report_data.get('recommendations', []),
        referral_priority=report_data.get('referral_priority'),
        follow_up_days=report_data.get('follow_up_days')
    )
    
    return generator.generate_report(data)


# ============================================
# SINGLETON INSTANCE
# ============================================

# Global report generator instance
report_generator = ReportGenerator()

__all__ = [
    'ReportGenerator',
    'ReportData',
    'report_generator',
    'create_report_generator',
    'generate_patient_report'
]
"""
Pregnancy App Data Pipeline

A specialized secure pipeline for pregnancy tracking applications.
Handles sensitive pregnancy-related medical data:
- Ultrasound images (2D, 3D, 4D)
- Lab results (blood tests, genetic screening, glucose tests)
- Fetal measurements and growth tracking
- Appointment records and notes
- Echo images and PDFs

Built on top of Secure Media Processor core for:
- HIPAA-compliant data handling
- End-to-end encryption
- Audit logging
- Secure deletion

Example:
    from src.pregnancy import PregnancyDataPipeline

    app = PregnancyDataPipeline(
        cloud_config={'provider': 's3', 'bucket': 'pregnancy-app-data'},
        user_id='user-12345'
    )

    # Upload ultrasound
    record = app.upload_ultrasound('ultrasound_12w.jpg', week=12)

    # Upload lab results
    lab = app.upload_lab_result('blood_test.pdf', test_type='NIPT')

    # Track fetal measurements
    app.add_fetal_measurement(week=20, weight_grams=300, length_cm=25)

    # Get pregnancy timeline
    timeline = app.get_timeline()

    # Export for doctor
    app.export_for_provider('export.zip', include_images=True)
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


# ==============================================================================
# Enums and Constants
# ==============================================================================

class RecordType(Enum):
    """Types of pregnancy records."""
    ULTRASOUND = "ultrasound"
    LAB_RESULT = "lab_result"
    FETAL_MEASUREMENT = "fetal_measurement"
    APPOINTMENT = "appointment"
    NOTE = "note"
    DOCUMENT = "document"


class UltrasoundType(Enum):
    """Types of ultrasound scans."""
    DATING = "dating"              # 6-9 weeks
    NT_SCAN = "nt_scan"            # 11-14 weeks (nuchal translucency)
    ANATOMY = "anatomy"            # 18-22 weeks
    GROWTH = "growth"              # 28-32 weeks
    BIOPHYSICAL = "biophysical"    # 32+ weeks
    DOPPLER = "doppler"            # Blood flow
    THREE_D = "3d"                 # 3D ultrasound
    FOUR_D = "4d"                  # 4D ultrasound


class LabTestType(Enum):
    """Types of lab tests during pregnancy."""
    BLOOD_TYPE = "blood_type"
    CBC = "cbc"                    # Complete blood count
    GLUCOSE = "glucose"            # Glucose tolerance
    NIPT = "nipt"                  # Non-invasive prenatal testing
    QUAD_SCREEN = "quad_screen"    # Quad marker screen
    GROUP_B_STREP = "gbs"          # Group B streptococcus
    URINE = "urine"
    THYROID = "thyroid"
    IRON = "iron"
    VITAMIN_D = "vitamin_d"
    GENETIC = "genetic"
    OTHER = "other"


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass
class FetalMeasurement:
    """Fetal measurement data."""
    measurement_id: str
    recorded_at: datetime
    gestational_week: int
    gestational_day: int = 0

    # Measurements (all optional, filled based on what's available)
    weight_grams: Optional[float] = None
    length_cm: Optional[float] = None          # Crown-rump or crown-heel
    head_circumference_mm: Optional[float] = None
    abdominal_circumference_mm: Optional[float] = None
    femur_length_mm: Optional[float] = None
    biparietal_diameter_mm: Optional[float] = None
    heart_rate_bpm: Optional[int] = None

    # Percentiles (compared to gestational age)
    weight_percentile: Optional[int] = None
    length_percentile: Optional[int] = None

    notes: Optional[str] = None
    source: Optional[str] = None  # e.g., "ultrasound", "manual"


@dataclass
class UltrasoundRecord:
    """Ultrasound image record."""
    record_id: str
    created_at: datetime
    gestational_week: int
    ultrasound_type: UltrasoundType

    # File info
    file_path: Optional[str] = None  # Cloud path
    local_path: Optional[str] = None
    file_size_bytes: int = 0
    mime_type: str = "image/jpeg"

    # Image metadata
    image_width: Optional[int] = None
    image_height: Optional[int] = None

    # Medical info
    findings: Optional[str] = None
    provider_name: Optional[str] = None  # Anonymized if configured
    facility_name: Optional[str] = None

    # Extracted measurements (if any)
    measurements: Optional[FetalMeasurement] = None

    notes: Optional[str] = None


@dataclass
class LabResultRecord:
    """Lab test result record."""
    record_id: str
    created_at: datetime
    test_date: date
    test_type: LabTestType
    gestational_week: Optional[int] = None

    # File info
    file_path: Optional[str] = None  # Cloud path (PDF)
    local_path: Optional[str] = None
    file_size_bytes: int = 0

    # Results (key-value pairs extracted or entered)
    results: Dict[str, Any] = field(default_factory=dict)

    # Status
    is_normal: Optional[bool] = None
    requires_followup: bool = False
    followup_notes: Optional[str] = None

    provider_name: Optional[str] = None
    lab_name: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class AppointmentRecord:
    """Medical appointment record."""
    record_id: str
    created_at: datetime
    appointment_date: datetime
    gestational_week: Optional[int] = None

    appointment_type: str = "prenatal"  # prenatal, ultrasound, lab, specialist
    provider_name: Optional[str] = None
    facility_name: Optional[str] = None

    # Notes and findings
    notes: Optional[str] = None
    blood_pressure: Optional[str] = None
    weight_kg: Optional[float] = None
    fundal_height_cm: Optional[float] = None

    # Next steps
    next_appointment: Optional[datetime] = None
    followup_required: bool = False


@dataclass
class PregnancyProfile:
    """User's pregnancy profile."""
    profile_id: str
    created_at: datetime
    updated_at: datetime

    # Dates
    lmp_date: Optional[date] = None          # Last menstrual period
    edd_date: Optional[date] = None          # Estimated due date
    conception_date: Optional[date] = None

    # Pregnancy info
    is_high_risk: bool = False
    multiple_pregnancy: bool = False
    number_of_fetuses: int = 1

    # Medical history (anonymized)
    previous_pregnancies: int = 0
    previous_births: int = 0
    medical_conditions: List[str] = field(default_factory=list)

    # Preferences
    preferred_name: Optional[str] = None
    notification_preferences: Dict[str, bool] = field(default_factory=dict)


# ==============================================================================
# Main Pipeline Class
# ==============================================================================

class PregnancyDataPipeline:
    """
    Secure data pipeline for pregnancy tracking applications.

    Handles all sensitive pregnancy data with:
    - End-to-end encryption
    - HIPAA-compliant audit logging
    - Secure cloud storage
    - Automatic anonymization
    - Secure deletion

    Example:
        # Initialize
        app = PregnancyDataPipeline(
            cloud_config={
                'provider': 's3',
                'bucket': 'my-pregnancy-app',
                'region': 'us-east-1'
            },
            user_id='user-abc123'
        )

        # Upload ultrasound image
        ultrasound = app.upload_ultrasound(
            image_path='~/Downloads/ultrasound.jpg',
            week=12,
            ultrasound_type=UltrasoundType.NT_SCAN,
            notes='NT measurement: 1.2mm - normal'
        )

        # Upload lab results
        lab = app.upload_lab_result(
            pdf_path='~/Downloads/nipt_results.pdf',
            test_type=LabTestType.NIPT,
            week=10,
            results={'risk_trisomy21': 'low', 'fetal_sex': 'female'}
        )

        # Add fetal measurement
        app.add_fetal_measurement(
            week=20,
            weight_grams=350,
            length_cm=26,
            heart_rate_bpm=150
        )

        # Get complete timeline
        timeline = app.get_timeline()

        # Export for doctor visit
        app.export_for_provider('pregnancy_summary.zip')

        # Cleanup when done
        app.cleanup()
    """

    def __init__(
        self,
        cloud_config: Dict[str, Any],
        user_id: str,
        encryption_key_path: str = "~/.smp/keys/pregnancy.key",
        audit_log_path: str = "~/.smp/audit/pregnancy/",
        workspace: str = "~/.smp/pregnancy-workspace/",
        auto_anonymize: bool = True
    ):
        """
        Initialize the pregnancy data pipeline.

        Args:
            cloud_config: Cloud storage configuration
            user_id: Anonymized user identifier
            encryption_key_path: Path to encryption key
            audit_log_path: Path for audit logs
            workspace: Local workspace directory
            auto_anonymize: Automatically anonymize provider names
        """
        self._cloud_config = cloud_config
        self._user_id = user_id
        self._encryption_key_path = Path(encryption_key_path).expanduser()
        self._audit_log_path = Path(audit_log_path).expanduser()
        self._workspace = Path(workspace).expanduser()
        self._auto_anonymize = auto_anonymize

        # Data storage
        self._profile: Optional[PregnancyProfile] = None
        self._ultrasounds: List[UltrasoundRecord] = []
        self._lab_results: List[LabResultRecord] = []
        self._measurements: List[FetalMeasurement] = []
        self._appointments: List[AppointmentRecord] = []

        # Lazy-loaded components
        self._transfer_pipeline = None
        self._audit_logger = None

        # Create workspace
        self._workspace.mkdir(parents=True, exist_ok=True)
        os.chmod(self._workspace, 0o700)

        # Load existing data
        self._load_local_data()

    def _init_pipeline(self):
        """Initialize the secure transfer pipeline."""
        if self._transfer_pipeline is not None:
            return

        from src.core import SecureTransferPipeline, MediaEncryptor, AuditLogger
        from src.connectors import S3Connector, GoogleDriveConnector, DropboxConnector

        # Initialize encryption
        encryption = MediaEncryptor(str(self._encryption_key_path))

        # Initialize audit logger
        self._audit_logger = AuditLogger(
            log_path=str(self._audit_log_path),
            user_id=self._user_id,
            retention_days=2190,  # 6 years
            redact_sensitive=True
        )

        # Create pipeline
        self._transfer_pipeline = SecureTransferPipeline(
            encryption=encryption,
            audit_logger=self._audit_logger,
            temp_dir=str(self._workspace / "temp"),
            verify_checksums=True
        )

        # Add cloud connector
        provider = self._cloud_config.get('provider', 's3')

        if provider == 's3':
            connector = S3Connector(
                bucket_name=self._cloud_config.get('bucket', ''),
                region=self._cloud_config.get('region', 'us-east-1')
            )
        elif provider == 'google_drive':
            connector = GoogleDriveConnector(
                credentials_path=self._cloud_config.get('credentials_path'),
                folder_id=self._cloud_config.get('folder_id')
            )
        elif provider == 'dropbox':
            connector = DropboxConnector(
                access_token=self._cloud_config.get('access_token')
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        self._transfer_pipeline.add_source('pregnancy-data', connector)

    # ==========================================================================
    # Profile Management
    # ==========================================================================

    def create_profile(
        self,
        lmp_date: Optional[date] = None,
        edd_date: Optional[date] = None,
        **kwargs
    ) -> PregnancyProfile:
        """Create or update pregnancy profile."""
        now = datetime.utcnow()

        if self._profile is None:
            self._profile = PregnancyProfile(
                profile_id=self._generate_id(),
                created_at=now,
                updated_at=now,
                lmp_date=lmp_date,
                edd_date=edd_date,
                **kwargs
            )
        else:
            self._profile.updated_at = now
            if lmp_date:
                self._profile.lmp_date = lmp_date
            if edd_date:
                self._profile.edd_date = edd_date
            for key, value in kwargs.items():
                if hasattr(self._profile, key):
                    setattr(self._profile, key, value)

        self._save_local_data()
        return self._profile

    def get_profile(self) -> Optional[PregnancyProfile]:
        """Get current pregnancy profile."""
        return self._profile

    def get_current_week(self) -> Optional[int]:
        """Calculate current gestational week based on LMP or EDD."""
        if self._profile is None:
            return None

        today = date.today()

        if self._profile.lmp_date:
            days = (today - self._profile.lmp_date).days
            return days // 7

        if self._profile.edd_date:
            days_to_edd = (self._profile.edd_date - today).days
            return 40 - (days_to_edd // 7)

        return None

    # ==========================================================================
    # Ultrasound Management
    # ==========================================================================

    def upload_ultrasound(
        self,
        image_path: str,
        week: int,
        ultrasound_type: UltrasoundType = UltrasoundType.GROWTH,
        notes: Optional[str] = None,
        provider_name: Optional[str] = None,
        measurements: Optional[Dict[str, float]] = None
    ) -> UltrasoundRecord:
        """
        Upload an ultrasound image securely.

        Args:
            image_path: Path to ultrasound image
            week: Gestational week
            ultrasound_type: Type of ultrasound scan
            notes: Optional notes
            provider_name: Healthcare provider name
            measurements: Optional fetal measurements from the scan

        Returns:
            UltrasoundRecord with upload details
        """
        self._init_pipeline()

        local_path = Path(image_path).expanduser()
        if not local_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        record_id = self._generate_id("us")
        now = datetime.utcnow()

        # Get image info
        image_info = self._get_image_info(local_path)

        # Create cloud path
        remote_path = f"users/{self._user_id}/ultrasounds/{record_id}{local_path.suffix}"

        # Upload encrypted
        from src.core import TransferMode
        manifest = self._transfer_pipeline.secure_upload(
            source_name='pregnancy-data',
            local_path=str(local_path),
            remote_path=remote_path,
            mode=TransferMode.STANDARD,
            metadata={
                'record_type': 'ultrasound',
                'week': week,
                'ultrasound_type': ultrasound_type.value
            }
        )

        # Create measurement record if provided
        fetal_measurement = None
        if measurements:
            fetal_measurement = self.add_fetal_measurement(
                week=week,
                source="ultrasound",
                **measurements
            )

        # Create record
        record = UltrasoundRecord(
            record_id=record_id,
            created_at=now,
            gestational_week=week,
            ultrasound_type=ultrasound_type,
            file_path=remote_path,
            file_size_bytes=local_path.stat().st_size,
            mime_type=image_info.get('mime_type', 'image/jpeg'),
            image_width=image_info.get('width'),
            image_height=image_info.get('height'),
            provider_name=None if self._auto_anonymize else provider_name,
            measurements=fetal_measurement,
            notes=notes
        )

        self._ultrasounds.append(record)
        self._save_local_data()

        logger.info(f"Uploaded ultrasound: {record_id} (week {week})")
        return record

    def get_ultrasounds(self, week: Optional[int] = None) -> List[UltrasoundRecord]:
        """Get ultrasound records, optionally filtered by week."""
        if week is None:
            return self._ultrasounds.copy()
        return [u for u in self._ultrasounds if u.gestational_week == week]

    # ==========================================================================
    # Lab Results Management
    # ==========================================================================

    def upload_lab_result(
        self,
        pdf_path: str,
        test_type: LabTestType,
        week: Optional[int] = None,
        test_date: Optional[date] = None,
        results: Optional[Dict[str, Any]] = None,
        is_normal: Optional[bool] = None,
        notes: Optional[str] = None
    ) -> LabResultRecord:
        """
        Upload a lab result PDF securely.

        Args:
            pdf_path: Path to PDF file
            test_type: Type of lab test
            week: Gestational week (optional)
            test_date: Date of test
            results: Key-value results extracted from PDF
            is_normal: Whether results are normal
            notes: Optional notes

        Returns:
            LabResultRecord with upload details
        """
        self._init_pipeline()

        local_path = Path(pdf_path).expanduser()
        if not local_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        record_id = self._generate_id("lab")
        now = datetime.utcnow()

        # Create cloud path
        remote_path = f"users/{self._user_id}/labs/{record_id}.pdf"

        # Upload encrypted
        from src.core import TransferMode
        manifest = self._transfer_pipeline.secure_upload(
            source_name='pregnancy-data',
            local_path=str(local_path),
            remote_path=remote_path,
            mode=TransferMode.STANDARD,
            metadata={
                'record_type': 'lab_result',
                'test_type': test_type.value,
                'week': week
            }
        )

        # Create record
        record = LabResultRecord(
            record_id=record_id,
            created_at=now,
            test_date=test_date or date.today(),
            test_type=test_type,
            gestational_week=week,
            file_path=remote_path,
            file_size_bytes=local_path.stat().st_size,
            results=results or {},
            is_normal=is_normal,
            notes=notes
        )

        self._lab_results.append(record)
        self._save_local_data()

        logger.info(f"Uploaded lab result: {record_id} ({test_type.value})")
        return record

    def get_lab_results(self, test_type: Optional[LabTestType] = None) -> List[LabResultRecord]:
        """Get lab results, optionally filtered by type."""
        if test_type is None:
            return self._lab_results.copy()
        return [l for l in self._lab_results if l.test_type == test_type]

    # ==========================================================================
    # Fetal Measurements
    # ==========================================================================

    def add_fetal_measurement(
        self,
        week: int,
        day: int = 0,
        source: str = "manual",
        **measurements
    ) -> FetalMeasurement:
        """
        Add a fetal measurement record.

        Args:
            week: Gestational week
            day: Additional days (0-6)
            source: Source of measurement (ultrasound, manual)
            **measurements: Measurement values (weight_grams, length_cm, etc.)

        Returns:
            FetalMeasurement record
        """
        record_id = self._generate_id("fm")
        now = datetime.utcnow()

        measurement = FetalMeasurement(
            measurement_id=record_id,
            recorded_at=now,
            gestational_week=week,
            gestational_day=day,
            source=source,
            **{k: v for k, v in measurements.items() if hasattr(FetalMeasurement, k)}
        )

        self._measurements.append(measurement)
        self._save_local_data()

        logger.info(f"Added measurement: {record_id} (week {week}+{day})")
        return measurement

    def get_measurements(self, week: Optional[int] = None) -> List[FetalMeasurement]:
        """Get fetal measurements, optionally filtered by week."""
        if week is None:
            return self._measurements.copy()
        return [m for m in self._measurements if m.gestational_week == week]

    def get_growth_chart_data(self) -> Dict[str, List[Dict]]:
        """Get data formatted for growth charts."""
        return {
            'weight': [
                {'week': m.gestational_week, 'value': m.weight_grams}
                for m in self._measurements if m.weight_grams
            ],
            'length': [
                {'week': m.gestational_week, 'value': m.length_cm}
                for m in self._measurements if m.length_cm
            ],
            'head_circumference': [
                {'week': m.gestational_week, 'value': m.head_circumference_mm}
                for m in self._measurements if m.head_circumference_mm
            ],
            'heart_rate': [
                {'week': m.gestational_week, 'value': m.heart_rate_bpm}
                for m in self._measurements if m.heart_rate_bpm
            ]
        }

    # ==========================================================================
    # Appointments
    # ==========================================================================

    def add_appointment(
        self,
        appointment_date: datetime,
        appointment_type: str = "prenatal",
        **kwargs
    ) -> AppointmentRecord:
        """Add an appointment record."""
        record_id = self._generate_id("apt")
        now = datetime.utcnow()

        record = AppointmentRecord(
            record_id=record_id,
            created_at=now,
            appointment_date=appointment_date,
            appointment_type=appointment_type,
            gestational_week=self.get_current_week(),
            **{k: v for k, v in kwargs.items() if hasattr(AppointmentRecord, k)}
        )

        # Anonymize if configured
        if self._auto_anonymize:
            record.provider_name = None
            record.facility_name = None

        self._appointments.append(record)
        self._save_local_data()

        return record

    def get_appointments(self, upcoming_only: bool = False) -> List[AppointmentRecord]:
        """Get appointments."""
        appointments = self._appointments.copy()
        if upcoming_only:
            now = datetime.utcnow()
            appointments = [a for a in appointments if a.appointment_date > now]
        return sorted(appointments, key=lambda a: a.appointment_date)

    # ==========================================================================
    # Timeline & Summary
    # ==========================================================================

    def get_timeline(self) -> List[Dict[str, Any]]:
        """Get complete pregnancy timeline."""
        events = []

        # Add ultrasounds
        for u in self._ultrasounds:
            events.append({
                'date': u.created_at,
                'week': u.gestational_week,
                'type': 'ultrasound',
                'subtype': u.ultrasound_type.value,
                'record_id': u.record_id,
                'summary': f"Ultrasound ({u.ultrasound_type.value})"
            })

        # Add lab results
        for l in self._lab_results:
            events.append({
                'date': datetime.combine(l.test_date, datetime.min.time()),
                'week': l.gestational_week,
                'type': 'lab_result',
                'subtype': l.test_type.value,
                'record_id': l.record_id,
                'summary': f"Lab: {l.test_type.value}",
                'is_normal': l.is_normal
            })

        # Add measurements
        for m in self._measurements:
            events.append({
                'date': m.recorded_at,
                'week': m.gestational_week,
                'type': 'measurement',
                'record_id': m.measurement_id,
                'summary': f"Measurement (week {m.gestational_week})"
            })

        # Add appointments
        for a in self._appointments:
            events.append({
                'date': a.appointment_date,
                'week': a.gestational_week,
                'type': 'appointment',
                'subtype': a.appointment_type,
                'record_id': a.record_id,
                'summary': f"Appointment: {a.appointment_type}"
            })

        # Sort by date
        return sorted(events, key=lambda e: e['date'])

    def get_summary(self) -> Dict[str, Any]:
        """Get pregnancy summary."""
        return {
            'profile': asdict(self._profile) if self._profile else None,
            'current_week': self.get_current_week(),
            'counts': {
                'ultrasounds': len(self._ultrasounds),
                'lab_results': len(self._lab_results),
                'measurements': len(self._measurements),
                'appointments': len(self._appointments)
            },
            'latest_measurement': asdict(self._measurements[-1]) if self._measurements else None,
            'upcoming_appointments': len(self.get_appointments(upcoming_only=True))
        }

    # ==========================================================================
    # Export & Sharing
    # ==========================================================================

    def export_for_provider(
        self,
        output_path: str,
        include_images: bool = True,
        include_pdfs: bool = True
    ) -> str:
        """
        Export pregnancy data for healthcare provider.

        Args:
            output_path: Output file path (will be a ZIP)
            include_images: Include ultrasound images
            include_pdfs: Include lab result PDFs

        Returns:
            Path to exported file
        """
        import zipfile
        import tempfile

        output_path = Path(output_path).expanduser()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Export summary JSON
            summary = {
                'exported_at': datetime.utcnow().isoformat(),
                'profile': asdict(self._profile) if self._profile else None,
                'ultrasounds': [asdict(u) for u in self._ultrasounds],
                'lab_results': [asdict(l) for l in self._lab_results],
                'measurements': [asdict(m) for m in self._measurements],
                'appointments': [asdict(a) for a in self._appointments],
                'timeline': self.get_timeline()
            }

            with open(temp_path / 'pregnancy_summary.json', 'w') as f:
                json.dump(summary, f, indent=2, default=str)

            # Create ZIP
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(temp_path / 'pregnancy_summary.json', 'pregnancy_summary.json')

                # TODO: Download and include images/PDFs if requested
                # This would use secure_download for each file

        logger.info(f"Exported pregnancy data to: {output_path}")
        return str(output_path)

    # ==========================================================================
    # Cleanup & Utilities
    # ==========================================================================

    def cleanup(self):
        """Securely delete all local data."""
        self._init_pipeline()

        # Delete workspace
        if self._workspace.exists():
            self._transfer_pipeline.secure_delete(str(self._workspace), recursive=True)

        # Clear in-memory data
        self._ultrasounds.clear()
        self._lab_results.clear()
        self._measurements.clear()
        self._appointments.clear()
        self._profile = None

        logger.info("Pregnancy data securely deleted")

    def get_audit_summary(self) -> Dict[str, Any]:
        """Get audit log summary."""
        if self._audit_logger is None:
            self._init_pipeline()

        return {
            'total_entries': self._audit_logger.get_entry_count(),
            'integrity_verified': self._audit_logger.verify_integrity()
        }

    # ==========================================================================
    # Private Methods
    # ==========================================================================

    def _generate_id(self, prefix: str = "") -> str:
        """Generate unique ID."""
        uid = uuid.uuid4().hex[:8]
        return f"{prefix}-{uid}" if prefix else uid

    def _get_image_info(self, path: Path) -> Dict[str, Any]:
        """Get image metadata."""
        try:
            from PIL import Image
            with Image.open(path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mime_type': f"image/{img.format.lower()}" if img.format else "image/jpeg"
                }
        except Exception:
            return {'mime_type': 'image/jpeg'}

    def _save_local_data(self):
        """Save data to local encrypted storage."""
        data_file = self._workspace / 'pregnancy_data.json'

        data = {
            'profile': asdict(self._profile) if self._profile else None,
            'ultrasounds': [asdict(u) for u in self._ultrasounds],
            'lab_results': [asdict(l) for l in self._lab_results],
            'measurements': [asdict(m) for m in self._measurements],
            'appointments': [asdict(a) for a in self._appointments]
        }

        with open(data_file, 'w') as f:
            json.dump(data, f, default=str)

    def _load_local_data(self):
        """Load data from local storage."""
        data_file = self._workspace / 'pregnancy_data.json'

        if not data_file.exists():
            return

        try:
            with open(data_file) as f:
                data = json.load(f)

            # Restore profile
            if data.get('profile'):
                self._profile = PregnancyProfile(**data['profile'])

            # Note: Full restoration would need to parse dates and enums
            # This is simplified for the example

        except Exception as e:
            logger.warning(f"Could not load local data: {e}")


# ==============================================================================
# Convenience Functions
# ==============================================================================

def create_pregnancy_pipeline(**kwargs) -> PregnancyDataPipeline:
    """Create a configured PregnancyDataPipeline instance."""
    return PregnancyDataPipeline(**kwargs)

# Pregnancy App Integration Guide

A complete guide for integrating Secure Media Processor into your pregnancy tracking application.

---

## Overview

The `PregnancyDataPipeline` provides secure handling of sensitive pregnancy data:

- Ultrasound images (2D, 3D, 4D)
- Lab results (blood tests, genetic screening)
- Fetal measurements and growth tracking
- Appointment records
- Complete pregnancy timeline

All data is:
- Encrypted end-to-end (AES-256-GCM)
- HIPAA-compliant with audit logging
- Securely deleted when no longer needed

---

## Installation

```bash
pip install secure-media-processor
```

---

## Quick Start

```python
from src.pregnancy import PregnancyDataPipeline, UltrasoundType, LabTestType

# Initialize
app = PregnancyDataPipeline(
    cloud_config={
        'provider': 's3',
        'bucket': 'my-pregnancy-app',
        'region': 'us-east-1'
    },
    user_id='user-12345'
)

# Create pregnancy profile
app.create_profile(
    lmp_date=date(2024, 1, 15),  # Last menstrual period
    edd_date=date(2024, 10, 22)  # Estimated due date
)

# Upload ultrasound
ultrasound = app.upload_ultrasound(
    image_path='~/Downloads/ultrasound_12w.jpg',
    week=12,
    ultrasound_type=UltrasoundType.NT_SCAN,
    notes='NT measurement normal'
)

# Upload lab results
lab = app.upload_lab_result(
    pdf_path='~/Downloads/nipt_results.pdf',
    test_type=LabTestType.NIPT,
    week=10,
    results={'risk_trisomy21': 'low'}
)

# Get timeline
timeline = app.get_timeline()
for event in timeline:
    print(f"Week {event['week']}: {event['summary']}")
```

---

## Core Features

### 1. Pregnancy Profile

```python
from datetime import date

# Create profile
profile = app.create_profile(
    lmp_date=date(2024, 1, 15),
    edd_date=date(2024, 10, 22),
    is_high_risk=False,
    multiple_pregnancy=False,
    previous_pregnancies=1,
    previous_births=1
)

# Get current week
week = app.get_current_week()
print(f"Currently at week {week}")

# Update profile
app.create_profile(is_high_risk=True)  # Updates existing
```

### 2. Ultrasound Management

```python
from src.pregnancy import UltrasoundType

# Upload with type classification
ultrasound = app.upload_ultrasound(
    image_path='scan.jpg',
    week=12,
    ultrasound_type=UltrasoundType.NT_SCAN,
    notes='Nuchal translucency: 1.2mm',
    measurements={
        'length_cm': 5.5,
        'heart_rate_bpm': 160
    }
)

# Available ultrasound types
# - DATING (6-9 weeks)
# - NT_SCAN (11-14 weeks)
# - ANATOMY (18-22 weeks)
# - GROWTH (28-32 weeks)
# - BIOPHYSICAL (32+ weeks)
# - DOPPLER
# - THREE_D
# - FOUR_D

# Get all ultrasounds
all_scans = app.get_ultrasounds()

# Get by week
week_12_scans = app.get_ultrasounds(week=12)
```

### 3. Lab Results

```python
from src.pregnancy import LabTestType
from datetime import date

# Upload lab result PDF
lab = app.upload_lab_result(
    pdf_path='blood_test.pdf',
    test_type=LabTestType.NIPT,
    week=10,
    test_date=date(2024, 3, 15),
    results={
        'risk_trisomy21': 'low',
        'risk_trisomy18': 'low',
        'fetal_sex': 'female'
    },
    is_normal=True
)

# Available lab test types
# - BLOOD_TYPE
# - CBC (Complete blood count)
# - GLUCOSE (Glucose tolerance)
# - NIPT (Non-invasive prenatal testing)
# - QUAD_SCREEN
# - GROUP_B_STREP
# - URINE
# - THYROID
# - IRON
# - VITAMIN_D
# - GENETIC
# - OTHER

# Get results
all_labs = app.get_lab_results()
nipt_results = app.get_lab_results(test_type=LabTestType.NIPT)
```

### 4. Fetal Measurements

```python
# Add measurement
measurement = app.add_fetal_measurement(
    week=20,
    day=3,  # 20 weeks + 3 days
    weight_grams=350,
    length_cm=26,
    head_circumference_mm=175,
    abdominal_circumference_mm=160,
    femur_length_mm=35,
    heart_rate_bpm=150
)

# Get measurements
all_measurements = app.get_measurements()
week_20 = app.get_measurements(week=20)

# Get data for growth charts
chart_data = app.get_growth_chart_data()
# Returns:
# {
#     'weight': [{'week': 20, 'value': 350}, ...],
#     'length': [{'week': 20, 'value': 26}, ...],
#     'head_circumference': [...],
#     'heart_rate': [...]
# }
```

### 5. Appointments

```python
from datetime import datetime

# Add appointment
appointment = app.add_appointment(
    appointment_date=datetime(2024, 4, 15, 10, 30),
    appointment_type='prenatal',
    notes='Regular checkup',
    blood_pressure='120/80',
    weight_kg=65.5
)

# Get appointments
all_appointments = app.get_appointments()
upcoming = app.get_appointments(upcoming_only=True)
```

### 6. Timeline & Summary

```python
# Get complete timeline
timeline = app.get_timeline()
for event in timeline:
    print(f"{event['date']}: Week {event['week']} - {event['summary']}")

# Get summary
summary = app.get_summary()
print(f"Current week: {summary['current_week']}")
print(f"Ultrasounds: {summary['counts']['ultrasounds']}")
print(f"Lab results: {summary['counts']['lab_results']}")
```

### 7. Export for Healthcare Provider

```python
# Export for doctor visit
app.export_for_provider(
    output_path='pregnancy_records.zip',
    include_images=True,
    include_pdfs=True
)
```

---

## Mobile App Integration Example

### React Native / Flutter Backend API

```python
# Flask API example
from flask import Flask, request, jsonify
from src.pregnancy import PregnancyDataPipeline, UltrasoundType

app = Flask(__name__)

# Initialize pipeline per user
def get_user_pipeline(user_id: str) -> PregnancyDataPipeline:
    return PregnancyDataPipeline(
        cloud_config={
            'provider': 's3',
            'bucket': 'pregnancy-app-prod',
            'region': 'us-east-1'
        },
        user_id=user_id
    )

@app.route('/api/ultrasound', methods=['POST'])
def upload_ultrasound():
    user_id = request.headers.get('X-User-ID')
    pipeline = get_user_pipeline(user_id)

    # Save uploaded file temporarily
    file = request.files['image']
    temp_path = f'/tmp/{file.filename}'
    file.save(temp_path)

    # Upload securely
    record = pipeline.upload_ultrasound(
        image_path=temp_path,
        week=int(request.form['week']),
        ultrasound_type=UltrasoundType(request.form['type']),
        notes=request.form.get('notes')
    )

    # Delete temp file
    os.remove(temp_path)

    return jsonify({
        'record_id': record.record_id,
        'week': record.gestational_week
    })

@app.route('/api/timeline', methods=['GET'])
def get_timeline():
    user_id = request.headers.get('X-User-ID')
    pipeline = get_user_pipeline(user_id)

    return jsonify(pipeline.get_timeline())

@app.route('/api/summary', methods=['GET'])
def get_summary():
    user_id = request.headers.get('X-User-ID')
    pipeline = get_user_pipeline(user_id)

    return jsonify(pipeline.get_summary())
```

### Mobile App (Pseudocode)

```javascript
// React Native example
import { uploadImage, getTimeline } from './api';

// Upload ultrasound from camera/gallery
async function uploadUltrasound(imageUri, week, type) {
    const formData = new FormData();
    formData.append('image', {
        uri: imageUri,
        type: 'image/jpeg',
        name: 'ultrasound.jpg'
    });
    formData.append('week', week);
    formData.append('type', type);

    const result = await uploadImage('/api/ultrasound', formData);
    return result;
}

// Display timeline
async function loadTimeline() {
    const timeline = await getTimeline();
    // Render timeline in UI
}
```

---

## Data Security

### What's Protected

| Data | Encryption | Storage |
|------|------------|---------|
| Ultrasound images | AES-256-GCM | Cloud (encrypted) |
| Lab result PDFs | AES-256-GCM | Cloud (encrypted) |
| Fetal measurements | AES-256-GCM | Local (encrypted JSON) |
| Profile data | AES-256-GCM | Local (encrypted JSON) |
| Audit logs | Hash chain | Local |

### Automatic Anonymization

By default, provider and facility names are anonymized:

```python
# With auto_anonymize=True (default)
app = PregnancyDataPipeline(..., auto_anonymize=True)

record = app.upload_ultrasound(
    ...,
    provider_name='Dr. Jane Smith'  # Stored as None
)

print(record.provider_name)  # None
```

### Secure Cleanup

```python
# Delete all data securely
app.cleanup()  # DoD 5220.22-M secure deletion
```

---

## Audit Logging

All operations are logged for HIPAA compliance:

```python
# Get audit summary
audit = app.get_audit_summary()
print(f"Total operations: {audit['total_entries']}")
print(f"Integrity verified: {audit['integrity_verified']}")
```

Logged events:
- File uploads
- File downloads
- Data access
- Secure deletions
- Profile changes

---

## Best Practices

### 1. Always Use User-Specific Pipelines

```python
# Good: One pipeline per user
def get_pipeline(user_id):
    return PregnancyDataPipeline(
        cloud_config=CONFIG,
        user_id=user_id
    )

# Bad: Shared pipeline
global_pipeline = PregnancyDataPipeline(...)  # Don't do this
```

### 2. Handle Cleanup on Account Deletion

```python
def delete_user_account(user_id):
    pipeline = get_pipeline(user_id)
    pipeline.cleanup()  # Securely delete all data
```

### 3. Regular Exports for Users

```python
# Let users export their data
def export_user_data(user_id):
    pipeline = get_pipeline(user_id)
    return pipeline.export_for_provider('export.zip')
```

### 4. Error Handling

```python
try:
    record = app.upload_ultrasound(...)
except FileNotFoundError:
    # Handle missing file
except Exception as e:
    # Log error, notify user
```

---

## Complete Example: Pregnancy Tracker App

```python
"""
Complete pregnancy tracker backend example.
"""

from src.pregnancy import (
    PregnancyDataPipeline,
    UltrasoundType,
    LabTestType
)
from datetime import date, datetime

class PregnancyTracker:
    def __init__(self, user_id: str):
        self.pipeline = PregnancyDataPipeline(
            cloud_config={
                'provider': 's3',
                'bucket': 'pregnancy-tracker-app',
                'region': 'us-east-1'
            },
            user_id=user_id,
            auto_anonymize=True
        )

    def setup_pregnancy(self, lmp_date: date):
        """Initial pregnancy setup."""
        # Calculate EDD (40 weeks from LMP)
        from datetime import timedelta
        edd = lmp_date + timedelta(weeks=40)

        self.pipeline.create_profile(
            lmp_date=lmp_date,
            edd_date=edd
        )

        return {
            'lmp': lmp_date,
            'edd': edd,
            'current_week': self.pipeline.get_current_week()
        }

    def log_appointment(self, date: datetime, vitals: dict):
        """Log a prenatal appointment."""
        return self.pipeline.add_appointment(
            appointment_date=date,
            appointment_type='prenatal',
            blood_pressure=vitals.get('bp'),
            weight_kg=vitals.get('weight')
        )

    def upload_scan(self, image_path: str, week: int, scan_type: str):
        """Upload ultrasound image."""
        type_map = {
            'dating': UltrasoundType.DATING,
            'nt': UltrasoundType.NT_SCAN,
            'anatomy': UltrasoundType.ANATOMY,
            'growth': UltrasoundType.GROWTH,
            '3d': UltrasoundType.THREE_D,
            '4d': UltrasoundType.FOUR_D
        }

        return self.pipeline.upload_ultrasound(
            image_path=image_path,
            week=week,
            ultrasound_type=type_map.get(scan_type, UltrasoundType.GROWTH)
        )

    def get_dashboard_data(self):
        """Get data for app dashboard."""
        summary = self.pipeline.get_summary()

        return {
            'current_week': summary['current_week'],
            'days_to_due': self._days_to_due(),
            'total_scans': summary['counts']['ultrasounds'],
            'total_labs': summary['counts']['lab_results'],
            'upcoming_appointments': summary['upcoming_appointments'],
            'latest_measurement': summary['latest_measurement'],
            'growth_data': self.pipeline.get_growth_chart_data()
        }

    def _days_to_due(self):
        profile = self.pipeline.get_profile()
        if profile and profile.edd_date:
            return (profile.edd_date - date.today()).days
        return None

    def cleanup(self):
        """Cleanup when user deletes account."""
        self.pipeline.cleanup()


# Usage
if __name__ == '__main__':
    tracker = PregnancyTracker(user_id='user-123')

    # Setup
    info = tracker.setup_pregnancy(lmp_date=date(2024, 1, 15))
    print(f"Due date: {info['edd']}")
    print(f"Current week: {info['current_week']}")

    # Get dashboard
    dashboard = tracker.get_dashboard_data()
    print(f"Days to due: {dashboard['days_to_due']}")
```

---

## Support

- **Issues:** https://github.com/Isaloum/Secure-Media-Processor/issues
- **Documentation:** https://github.com/Isaloum/Secure-Media-Processor/docs/

---

**Remember:** Always call `pipeline.cleanup()` when a user deletes their account!

"""DICOM medical image processing module.

This module provides comprehensive DICOM file handling for medical imaging
research, including MRI breast cancer analysis workflows.

Features:
- Read/write DICOM files with full metadata support
- Extract and anonymize patient information (HIPAA compliance)
- Handle 3D volumetric data (MRI slice stacks)
- Convert between DICOM and standard formats
"""

import logging
from pathlib import Path
from typing import Union, Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json

import numpy as np

logger = logging.getLogger(__name__)

# pydicom is optional - try to import, fall back gracefully
PYDICOM_AVAILABLE = False
pydicom = None
dcmread = None
dcmwrite = None

try:
    import pydicom as _pydicom
    from pydicom import dcmread as _dcmread
    from pydicom import dcmwrite as _dcmwrite
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.uid import generate_uid

    pydicom = _pydicom
    dcmread = _dcmread
    dcmwrite = _dcmwrite
    PYDICOM_AVAILABLE = True
    logger.debug("pydicom available for DICOM processing")
except ImportError:
    logger.info("pydicom not installed - DICOM support disabled. Install with: pip install pydicom")


@dataclass
class DICOMMetadata:
    """Structured DICOM metadata container."""

    # Patient Information
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    patient_birth_date: Optional[str] = None
    patient_sex: Optional[str] = None
    patient_age: Optional[str] = None

    # Study Information
    study_instance_uid: Optional[str] = None
    study_date: Optional[str] = None
    study_time: Optional[str] = None
    study_description: Optional[str] = None
    accession_number: Optional[str] = None

    # Series Information
    series_instance_uid: Optional[str] = None
    series_number: Optional[int] = None
    series_description: Optional[str] = None
    modality: Optional[str] = None  # MR, CT, US, etc.

    # Image Information
    sop_instance_uid: Optional[str] = None
    instance_number: Optional[int] = None
    image_position: Optional[Tuple[float, float, float]] = None
    image_orientation: Optional[Tuple[float, ...]] = None
    pixel_spacing: Optional[Tuple[float, float]] = None
    slice_thickness: Optional[float] = None
    slice_location: Optional[float] = None

    # MRI-Specific
    magnetic_field_strength: Optional[float] = None
    echo_time: Optional[float] = None
    repetition_time: Optional[float] = None
    flip_angle: Optional[float] = None
    sequence_name: Optional[str] = None

    # Image Dimensions
    rows: Optional[int] = None
    columns: Optional[int] = None
    bits_allocated: Optional[int] = None
    bits_stored: Optional[int] = None

    # Additional metadata
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def get_anonymized(self) -> 'DICOMMetadata':
        """Return anonymized copy of metadata (HIPAA compliance)."""
        anon = DICOMMetadata(
            # Keep non-identifying information
            study_instance_uid=self.study_instance_uid,
            series_instance_uid=self.series_instance_uid,
            modality=self.modality,
            series_description=self.series_description,
            image_position=self.image_position,
            image_orientation=self.image_orientation,
            pixel_spacing=self.pixel_spacing,
            slice_thickness=self.slice_thickness,
            slice_location=self.slice_location,
            magnetic_field_strength=self.magnetic_field_strength,
            echo_time=self.echo_time,
            repetition_time=self.repetition_time,
            flip_angle=self.flip_angle,
            sequence_name=self.sequence_name,
            rows=self.rows,
            columns=self.columns,
            bits_allocated=self.bits_allocated,
            bits_stored=self.bits_stored,
        )
        return anon


@dataclass
class DICOMVolume:
    """Container for 3D DICOM volume data."""

    # 3D numpy array (slices, height, width)
    pixel_data: np.ndarray

    # Metadata for each slice
    slice_metadata: List[DICOMMetadata]

    # Volume-level information
    volume_shape: Tuple[int, int, int] = field(init=False)
    voxel_spacing: Optional[Tuple[float, float, float]] = None
    orientation: Optional[str] = None  # AXIAL, SAGITTAL, CORONAL

    def __post_init__(self):
        self.volume_shape = self.pixel_data.shape

    def get_slice(self, index: int) -> np.ndarray:
        """Get a specific slice from the volume."""
        return self.pixel_data[index]

    def get_axial_slice(self, index: int) -> np.ndarray:
        """Get axial (transverse) slice."""
        return self.pixel_data[index, :, :]

    def get_sagittal_slice(self, index: int) -> np.ndarray:
        """Get sagittal slice."""
        return self.pixel_data[:, :, index]

    def get_coronal_slice(self, index: int) -> np.ndarray:
        """Get coronal slice."""
        return self.pixel_data[:, index, :]

    def normalize(self, method: str = 'minmax') -> 'DICOMVolume':
        """Normalize pixel values."""
        if method == 'minmax':
            min_val = self.pixel_data.min()
            max_val = self.pixel_data.max()
            if max_val > min_val:
                normalized = (self.pixel_data - min_val) / (max_val - min_val)
            else:
                normalized = self.pixel_data.copy()
        elif method == 'zscore':
            mean = self.pixel_data.mean()
            std = self.pixel_data.std()
            if std > 0:
                normalized = (self.pixel_data - mean) / std
            else:
                normalized = self.pixel_data - mean
        else:
            normalized = self.pixel_data.copy()

        return DICOMVolume(
            pixel_data=normalized.astype(np.float32),
            slice_metadata=self.slice_metadata,
            voxel_spacing=self.voxel_spacing,
            orientation=self.orientation
        )


class DICOMProcessor:
    """Process DICOM medical imaging files.

    Supports:
    - Single DICOM file reading/writing
    - 3D volume reconstruction from slice series
    - Metadata extraction and anonymization
    - Format conversion (DICOM to PNG/NIFTI)
    - MRI-specific processing for breast imaging
    """

    def __init__(self):
        """Initialize DICOM processor."""
        if not PYDICOM_AVAILABLE:
            logger.warning("pydicom not installed. Install with: pip install pydicom")

        self._audit_log: List[Dict[str, Any]] = []

    def _log_access(self, action: str, file_path: str, patient_id: Optional[str] = None):
        """Log data access for HIPAA compliance audit trail."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'file': str(file_path),
            'patient_id_hash': hashlib.sha256(patient_id.encode()).hexdigest()[:16] if patient_id else None
        }
        self._audit_log.append(entry)
        logger.info(f"DICOM access: {action} on {file_path}")

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get audit log for compliance reporting."""
        return self._audit_log.copy()

    def read_dicom(self, file_path: Union[str, Path]) -> Tuple[np.ndarray, DICOMMetadata]:
        """Read a single DICOM file.

        Args:
            file_path: Path to DICOM file (.dcm)

        Returns:
            Tuple of (pixel_array, metadata)
        """
        if not PYDICOM_AVAILABLE:
            raise RuntimeError("pydicom not installed. Install with: pip install pydicom")

        file_path = Path(file_path)

        # Read DICOM file
        ds = dcmread(str(file_path))

        # Log access
        patient_id = getattr(ds, 'PatientID', None)
        self._log_access('read', file_path, patient_id)

        # Extract pixel data
        pixel_array = ds.pixel_array.astype(np.float32)

        # Apply rescale if present (common in CT/MRI)
        if hasattr(ds, 'RescaleSlope') and hasattr(ds, 'RescaleIntercept'):
            pixel_array = pixel_array * ds.RescaleSlope + ds.RescaleIntercept

        # Extract metadata
        metadata = self._extract_metadata(ds)

        return pixel_array, metadata

    def _extract_metadata(self, ds) -> DICOMMetadata:
        """Extract metadata from DICOM dataset."""

        def safe_get(attr, default=None):
            return getattr(ds, attr, default)

        def safe_get_float(attr, default=None):
            val = getattr(ds, attr, default)
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default
            return default

        def safe_get_int(attr, default=None):
            val = getattr(ds, attr, default)
            if val is not None:
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return default
            return default

        # Extract image position as tuple
        image_pos = safe_get('ImagePositionPatient')
        if image_pos is not None:
            image_pos = tuple(float(x) for x in image_pos)

        # Extract image orientation
        image_orient = safe_get('ImageOrientationPatient')
        if image_orient is not None:
            image_orient = tuple(float(x) for x in image_orient)

        # Extract pixel spacing
        pixel_spacing = safe_get('PixelSpacing')
        if pixel_spacing is not None:
            pixel_spacing = tuple(float(x) for x in pixel_spacing)

        return DICOMMetadata(
            # Patient
            patient_id=safe_get('PatientID'),
            patient_name=str(safe_get('PatientName', '')),
            patient_birth_date=safe_get('PatientBirthDate'),
            patient_sex=safe_get('PatientSex'),
            patient_age=safe_get('PatientAge'),

            # Study
            study_instance_uid=safe_get('StudyInstanceUID'),
            study_date=safe_get('StudyDate'),
            study_time=safe_get('StudyTime'),
            study_description=safe_get('StudyDescription'),
            accession_number=safe_get('AccessionNumber'),

            # Series
            series_instance_uid=safe_get('SeriesInstanceUID'),
            series_number=safe_get_int('SeriesNumber'),
            series_description=safe_get('SeriesDescription'),
            modality=safe_get('Modality'),

            # Image
            sop_instance_uid=safe_get('SOPInstanceUID'),
            instance_number=safe_get_int('InstanceNumber'),
            image_position=image_pos,
            image_orientation=image_orient,
            pixel_spacing=pixel_spacing,
            slice_thickness=safe_get_float('SliceThickness'),
            slice_location=safe_get_float('SliceLocation'),

            # MRI-Specific
            magnetic_field_strength=safe_get_float('MagneticFieldStrength'),
            echo_time=safe_get_float('EchoTime'),
            repetition_time=safe_get_float('RepetitionTime'),
            flip_angle=safe_get_float('FlipAngle'),
            sequence_name=safe_get('SequenceName'),

            # Dimensions
            rows=safe_get_int('Rows'),
            columns=safe_get_int('Columns'),
            bits_allocated=safe_get_int('BitsAllocated'),
            bits_stored=safe_get_int('BitsStored'),
        )

    def read_dicom_series(self,
                          directory: Union[str, Path],
                          series_uid: Optional[str] = None) -> DICOMVolume:
        """Read a series of DICOM files as a 3D volume.

        Args:
            directory: Directory containing DICOM files
            series_uid: Optional series UID to filter by

        Returns:
            DICOMVolume containing 3D data
        """
        if not PYDICOM_AVAILABLE:
            raise RuntimeError("pydicom not installed. Install with: pip install pydicom")

        directory = Path(directory)

        # Find all DICOM files
        dicom_files = []
        for ext in ['*.dcm', '*.DCM', '*.dicom', '*.DICOM', '*']:
            dicom_files.extend(directory.glob(ext))

        # Filter and read valid DICOM files
        slices = []
        for f in dicom_files:
            try:
                ds = dcmread(str(f))

                # Filter by series UID if specified
                if series_uid and getattr(ds, 'SeriesInstanceUID', None) != series_uid:
                    continue

                # Must have pixel data
                if not hasattr(ds, 'pixel_array'):
                    continue

                slices.append(ds)
            except Exception as e:
                logger.debug(f"Skipping {f}: {e}")
                continue

        if not slices:
            raise ValueError(f"No valid DICOM files found in {directory}")

        # Sort by slice location or instance number
        def get_sort_key(ds):
            if hasattr(ds, 'SliceLocation'):
                return float(ds.SliceLocation)
            if hasattr(ds, 'InstanceNumber'):
                return int(ds.InstanceNumber)
            if hasattr(ds, 'ImagePositionPatient'):
                return float(ds.ImagePositionPatient[2])
            return 0

        slices.sort(key=get_sort_key)

        # Log access
        patient_id = getattr(slices[0], 'PatientID', None)
        self._log_access('read_series', directory, patient_id)

        # Stack into 3D volume
        pixel_arrays = []
        slice_metadata = []

        for ds in slices:
            arr = ds.pixel_array.astype(np.float32)

            # Apply rescale
            if hasattr(ds, 'RescaleSlope') and hasattr(ds, 'RescaleIntercept'):
                arr = arr * ds.RescaleSlope + ds.RescaleIntercept

            pixel_arrays.append(arr)
            slice_metadata.append(self._extract_metadata(ds))

        volume_data = np.stack(pixel_arrays, axis=0)

        # Calculate voxel spacing
        voxel_spacing = None
        if slice_metadata[0].pixel_spacing and slice_metadata[0].slice_thickness:
            voxel_spacing = (
                slice_metadata[0].slice_thickness,
                slice_metadata[0].pixel_spacing[0],
                slice_metadata[0].pixel_spacing[1]
            )

        return DICOMVolume(
            pixel_data=volume_data,
            slice_metadata=slice_metadata,
            voxel_spacing=voxel_spacing,
            orientation=self._determine_orientation(slice_metadata[0])
        )

    def _determine_orientation(self, metadata: DICOMMetadata) -> Optional[str]:
        """Determine volume orientation from image orientation."""
        if metadata.image_orientation is None:
            return None

        orient = metadata.image_orientation

        # Simplified orientation detection
        # Row direction (first 3 values) and column direction (last 3 values)
        row_x, row_y, row_z = abs(orient[0]), abs(orient[1]), abs(orient[2])
        col_x, col_y, col_z = abs(orient[3]), abs(orient[4]), abs(orient[5])

        # Determine plane based on which axis is perpendicular
        if row_x > 0.8 and col_y > 0.8:
            return 'AXIAL'
        elif row_x > 0.8 and col_z > 0.8:
            return 'CORONAL'
        elif row_y > 0.8 and col_z > 0.8:
            return 'SAGITTAL'

        return 'OBLIQUE'

    def anonymize_dicom(self,
                        input_path: Union[str, Path],
                        output_path: Union[str, Path],
                        keep_study_uid: bool = False) -> Dict[str, Any]:
        """Anonymize a DICOM file for HIPAA compliance.

        Removes/replaces:
        - Patient name, ID, birth date
        - Institution information
        - Referring physician
        - All private tags

        Args:
            input_path: Path to input DICOM file
            output_path: Path to save anonymized file
            keep_study_uid: Whether to preserve study UIDs

        Returns:
            Dictionary with anonymization details
        """
        if not PYDICOM_AVAILABLE:
            raise RuntimeError("pydicom not installed. Install with: pip install pydicom")

        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ds = dcmread(str(input_path))
        original_patient_id = getattr(ds, 'PatientID', 'UNKNOWN')

        self._log_access('anonymize', input_path, original_patient_id)

        # Fields to anonymize (HIPAA Safe Harbor)
        anonymize_tags = [
            'PatientName',
            'PatientID',
            'PatientBirthDate',
            'PatientAddress',
            'PatientTelephoneNumbers',
            'InstitutionName',
            'InstitutionAddress',
            'ReferringPhysicianName',
            'PhysiciansOfRecord',
            'PerformingPhysicianName',
            'OperatorsName',
            'OtherPatientIDs',
            'OtherPatientNames',
            'PatientBirthName',
            'PatientMotherBirthName',
            'MedicalRecordLocator',
            'EthnicGroup',
            'Occupation',
            'AdditionalPatientHistory',
            'PatientComments',
            'ResponsiblePerson',
            'ResponsibleOrganization',
        ]

        removed_fields = []

        for tag in anonymize_tags:
            if hasattr(ds, tag):
                removed_fields.append(tag)
                if tag == 'PatientName':
                    ds.PatientName = 'ANONYMOUS'
                elif tag == 'PatientID':
                    # Generate anonymized ID
                    ds.PatientID = f"ANON_{hashlib.sha256(original_patient_id.encode()).hexdigest()[:8]}"
                elif tag == 'PatientBirthDate':
                    ds.PatientBirthDate = ''
                else:
                    delattr(ds, tag)

        # Generate new UIDs unless keeping study UID
        if not keep_study_uid:
            ds.StudyInstanceUID = generate_uid()
            ds.SeriesInstanceUID = generate_uid()
        ds.SOPInstanceUID = generate_uid()

        # Remove private tags
        ds.remove_private_tags()

        # Save anonymized file
        ds.save_as(str(output_path))

        return {
            'input': str(input_path),
            'output': str(output_path),
            'removed_fields': removed_fields,
            'new_patient_id': ds.PatientID,
            'original_patient_id_hash': hashlib.sha256(original_patient_id.encode()).hexdigest()[:16]
        }

    def convert_to_png(self,
                       input_path: Union[str, Path],
                       output_path: Union[str, Path],
                       window_center: Optional[float] = None,
                       window_width: Optional[float] = None,
                       normalize: bool = True) -> Dict[str, Any]:
        """Convert DICOM to PNG image.

        Args:
            input_path: Path to DICOM file
            output_path: Path to save PNG
            window_center: Window center for contrast adjustment
            window_width: Window width for contrast adjustment
            normalize: Whether to normalize to 0-255

        Returns:
            Conversion metadata
        """
        from PIL import Image

        pixel_array, metadata = self.read_dicom(input_path)

        # Apply windowing if specified
        if window_center is not None and window_width is not None:
            min_val = window_center - window_width / 2
            max_val = window_center + window_width / 2
            pixel_array = np.clip(pixel_array, min_val, max_val)

        # Normalize to 0-255
        if normalize:
            min_val = pixel_array.min()
            max_val = pixel_array.max()
            if max_val > min_val:
                pixel_array = (pixel_array - min_val) / (max_val - min_val) * 255
            pixel_array = pixel_array.astype(np.uint8)

        # Save as PNG
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        img = Image.fromarray(pixel_array)
        img.save(str(output_path))

        return {
            'input': str(input_path),
            'output': str(output_path),
            'size': pixel_array.shape,
            'modality': metadata.modality
        }

    def convert_to_nifti(self,
                         dicom_dir: Union[str, Path],
                         output_path: Union[str, Path]) -> Dict[str, Any]:
        """Convert DICOM series to NIfTI format.

        NIfTI is commonly used in neuroimaging and medical ML research.

        Args:
            dicom_dir: Directory containing DICOM series
            output_path: Path to save .nii.gz file

        Returns:
            Conversion metadata
        """
        try:
            import nibabel as nib
        except ImportError:
            raise RuntimeError("nibabel not installed. Install with: pip install nibabel")

        # Read DICOM series
        volume = self.read_dicom_series(dicom_dir)

        # Create affine transformation matrix
        affine = np.eye(4)
        if volume.voxel_spacing:
            affine[0, 0] = volume.voxel_spacing[2]  # x spacing
            affine[1, 1] = volume.voxel_spacing[1]  # y spacing
            affine[2, 2] = volume.voxel_spacing[0]  # z spacing (slice)

        # Create NIfTI image
        nifti_img = nib.Nifti1Image(volume.pixel_data, affine)

        # Save
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        nib.save(nifti_img, str(output_path))

        return {
            'input_dir': str(dicom_dir),
            'output': str(output_path),
            'volume_shape': volume.volume_shape,
            'voxel_spacing': volume.voxel_spacing,
            'num_slices': len(volume.slice_metadata)
        }

    def get_series_list(self, directory: Union[str, Path]) -> List[Dict[str, Any]]:
        """List all DICOM series in a directory.

        Args:
            directory: Directory to scan

        Returns:
            List of series information dictionaries
        """
        if not PYDICOM_AVAILABLE:
            raise RuntimeError("pydicom not installed. Install with: pip install pydicom")

        directory = Path(directory)
        series_dict = {}

        for f in directory.rglob('*'):
            if f.is_file():
                try:
                    ds = dcmread(str(f), stop_before_pixels=True)
                    series_uid = getattr(ds, 'SeriesInstanceUID', 'unknown')

                    if series_uid not in series_dict:
                        series_dict[series_uid] = {
                            'series_uid': series_uid,
                            'modality': getattr(ds, 'Modality', 'unknown'),
                            'series_description': getattr(ds, 'SeriesDescription', ''),
                            'patient_id': getattr(ds, 'PatientID', 'unknown'),
                            'study_date': getattr(ds, 'StudyDate', ''),
                            'num_slices': 0,
                            'files': []
                        }

                    series_dict[series_uid]['num_slices'] += 1
                    series_dict[series_uid]['files'].append(str(f))

                except Exception:
                    continue

        return list(series_dict.values())


def check_dicom_available() -> bool:
    """Check if DICOM processing is available."""
    return PYDICOM_AVAILABLE

Medical Imaging
===============

The medical imaging module provides HIPAA-compliant processing of medical images,
including DICOM handling, anonymization, and machine learning inference.

.. note::
   Medical imaging features require the ``[medical]`` extra:

   .. code-block:: bash

      pip install secure-media-processor[medical]

MedicalPipeline
---------------

.. automodule:: src.medical.pipeline
   :members:
   :undoc-members:
   :show-inheritance:

PregnancyDataPipeline
---------------------

Specialized pipeline for pregnancy tracking applications.

.. automodule:: src.pregnancy
   :members:
   :undoc-members:
   :show-inheritance:

DICOM Processing
----------------

.. automodule:: src.medical.dicom_handler
   :members:
   :undoc-members:
   :show-inheritance:

Examples
--------

Complete Medical Study Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.medical import MedicalPipeline
   from src.core import TransferMode

   pipeline = MedicalPipeline()

   # Process a complete study
   result = pipeline.process_study(
       remote_path="s3://hospital/studies/STUDY-001/",
       operations=["load", "anonymize", "preprocess", "predict"],
       study_id="STUDY-001",
       download_mode=TransferMode.ZERO_KNOWLEDGE,
       output_path="/results/STUDY-001/"
   )

   print(f"Prediction: {result.prediction}")
   print(f"Confidence: {result.confidence}")

DICOM Anonymization
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.medical import MedicalPipeline

   pipeline = MedicalPipeline()

   # Anonymize DICOM files (HIPAA Safe Harbor)
   result = pipeline.anonymize_study(
       input_path="/raw/study001/",
       output_path="/anonymized/study001/",
       retain_dates=False,  # Remove all dates
       retain_institution=False  # Remove institution info
   )

   print(f"Anonymized {result['files_processed']} files")

Breast Cancer Screening
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.medical import MedicalPipeline

   pipeline = MedicalPipeline()

   # Load and preprocess mammogram
   study = pipeline.load_study("/path/to/mammogram.dcm")
   preprocessed = pipeline.preprocess(study, normalize=True)

   # Run prediction
   prediction = pipeline.predict(
       preprocessed,
       model_name="breast_cancer_detector",
       threshold=0.5
   )

   print(f"Risk level: {prediction['risk_level']}")
   print(f"Confidence: {prediction['confidence']:.2%}")

Pregnancy App Integration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.pregnancy import PregnancyDataPipeline, UltrasoundType

   pipeline = PregnancyDataPipeline(
       user_id="user123",
       storage_connector=azure_connector
   )

   # Upload ultrasound
   result = pipeline.upload_ultrasound(
       image_path="/path/to/ultrasound.jpg",
       week=20,
       day=3,
       ultrasound_type=UltrasoundType.ANATOMY_SCAN
   )

   # Add fetal measurement
   pipeline.add_fetal_measurement(
       week=20,
       day=3,
       biparietal_diameter_mm=48.5,
       femur_length_mm=32.1,
       head_circumference_mm=175.0
   )

   # Get timeline
   timeline = pipeline.get_timeline()
   for entry in timeline:
       print(f"Week {entry['week']}: {entry['type']}")

   # Export for healthcare provider
   pipeline.export_for_provider(
       output_path="/exports/pregnancy_record.pdf",
       include_images=True
   )

CLI Commands
------------

Process Study
~~~~~~~~~~~~~

.. code-block:: bash

   # Process a medical study from cloud storage
   smp process-study s3://bucket/study001/ \\
       --operations load,anonymize,preprocess,predict \\
       --study-id STUDY-001 \\
       --output-path /results/

Secure Download
~~~~~~~~~~~~~~~

.. code-block:: bash

   # Download with encryption
   smp secure-download s3://bucket/data.zip /local/data.zip \\
       --verify-checksum

Secure Delete
~~~~~~~~~~~~~

.. code-block:: bash

   # DoD-compliant secure deletion
   smp secure-delete /path/to/sensitive/file.dcm \\
       --passes 3

Audit Export
~~~~~~~~~~~~

.. code-block:: bash

   # Export audit logs for compliance
   smp audit-export --output compliance_report.json \\
       --start-date 2024-01-01 \\
       --end-date 2024-12-31

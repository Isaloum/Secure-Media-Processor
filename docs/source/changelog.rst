Changelog
=========

All notable changes to Secure Media Processor.

[2.3.0] - 2024
--------------

Added
~~~~~
* OneDrive connector with Microsoft Graph API support
* Comprehensive Sphinx API documentation
* Interactive demo scripts (``demo/demo_secure_pipeline.py``)
* Quick demo for CI testing (``demo/quick_demo.py``)
* Additional test coverage for Azure and OneDrive connectors
* Core module integration tests

Changed
~~~~~~~
* Enhanced CI/CD pipeline with multi-Python version testing
* Updated Docker configurations for better production use

[2.2.0] - 2024
--------------

Added
~~~~~
* Azure Blob Storage connector (``AzureBlobConnector``)
* SAS URL generation for temporary access sharing
* Docker medical service configuration
* Azure environment variables in Docker Compose

Changed
~~~~~~~
* Updated Dockerfiles to use pyproject.toml
* Improved Docker multi-stage builds

[2.1.0] - 2024
--------------

Added
~~~~~
* Pregnancy app module (``PregnancyDataPipeline``)
* Fetal measurement tracking with growth percentiles
* Ultrasound and lab result management
* Healthcare provider export functionality

[2.0.0] - 2024
--------------

Major refactoring release focusing on core mission: secure data pipeline.

Added
~~~~~
* ``SecureTransferPipeline`` - Core secure transfer functionality
* ``KeyExchange`` - ECDH key exchange for multi-party transfers
* ``AuditLogger`` - HIPAA-compliant audit logging with hash chains
* ``MedicalPipeline`` - Integrated medical imaging workflow
* New CLI commands: ``process-study``, ``secure-download``, ``secure-delete``, ``audit-export``
* Plugin architecture for domain-specific extensions
* Comprehensive documentation (ROADMAP.md, SECURITY_MODEL.md, DATA_FLOW.md)

Changed
~~~~~~~
* Restructured as secure data pipeline (from media processor)
* Medical imaging moved to dedicated module
* Updated README with new project vision

[1.1.0] - 2024
--------------

Added
~~~~~
* Initial cloud connector implementations
* S3, Google Drive, Dropbox support
* Rate limiting for API calls
* Credential cleanup on disconnect

[1.0.0] - 2024
--------------

Initial release.

* Basic encryption/decryption
* GPU-accelerated processing
* Cloud storage integration

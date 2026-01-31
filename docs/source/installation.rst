Installation
============

Requirements
------------

* Python 3.8 or higher
* pip (Python package manager)

Basic Installation
------------------

Install the base package from PyPI:

.. code-block:: bash

   pip install secure-media-processor

Optional Dependencies
---------------------

Install with specific feature sets:

.. code-block:: bash

   # Medical imaging (DICOM, segmentation, ML)
   pip install secure-media-processor[medical]

   # GPU acceleration (PyTorch)
   pip install secure-media-processor[gpu]

   # Azure Blob Storage
   pip install secure-media-processor[azure]

   # OneDrive support
   pip install secure-media-processor[onedrive]

   # Development tools
   pip install secure-media-processor[dev]

   # Everything
   pip install secure-media-processor[all]

Docker Installation
-------------------

Using Docker Compose:

.. code-block:: bash

   # CPU version
   docker-compose up smp

   # GPU version (requires nvidia-container-toolkit)
   docker-compose up smp-gpu

   # Medical processing
   docker-compose up smp-medical

Building from Source
--------------------

.. code-block:: bash

   git clone https://github.com/Isaloum/Secure-Media-Processor.git
   cd Secure-Media-Processor
   pip install -e ".[dev]"

Verifying Installation
----------------------

Run the quick demo to verify everything is working:

.. code-block:: bash

   python demo/quick_demo.py

Or test specific components:

.. code-block:: python

   from src.core import SecureTransferPipeline, AuditLogger, KeyExchange
   from src.connectors import S3Connector, AZURE_AVAILABLE

   print("Core modules loaded successfully!")
   print(f"Azure support: {AZURE_AVAILABLE}")

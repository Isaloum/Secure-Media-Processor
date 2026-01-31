Secure Media Processor Documentation
=====================================

.. image:: https://img.shields.io/pypi/v/secure-media-processor.svg
   :target: https://pypi.org/project/secure-media-processor/

.. image:: https://img.shields.io/pypi/pyversions/secure-media-processor.svg
   :target: https://pypi.org/project/secure-media-processor/

**Secure Media Processor** is a secure data pipeline for transferring sensitive data
from cloud storage to local GPU processing. Built with HIPAA compliance in mind,
it provides end-to-end encryption, secure key exchange, and comprehensive audit logging.

Key Features
------------

* **End-to-End Encryption**: AES-256-GCM authenticated encryption
* **Secure Key Exchange**: ECDH (Elliptic Curve Diffie-Hellman) for multi-party transfers
* **HIPAA-Compliant Audit Logging**: Hash-chained logs for tamper detection
* **Secure Deletion**: DoD 5220.22-M compliant 3-pass overwrite
* **Multi-Cloud Support**: AWS S3, Google Drive, Dropbox, Azure Blob, OneDrive
* **Medical Imaging**: DICOM processing, anonymization, and ML inference

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   # Basic installation
   pip install secure-media-processor

   # With medical imaging support
   pip install secure-media-processor[medical]

   # With all cloud connectors
   pip install secure-media-processor[all]

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from src.core import SecureTransferPipeline, KeyExchange

   # Initialize key exchange
   key_exchange = KeyExchange()
   private_key, public_key = key_exchange.generate_ecdh_keypair()

   # Initialize secure pipeline
   pipeline = SecureTransferPipeline()

   # Download and process securely
   result = pipeline.secure_download(
       remote_path="s3://bucket/sensitive-data.zip",
       local_path="/tmp/data.zip",
       verify_checksum=True
   )

   # Secure deletion after processing
   pipeline.secure_delete("/tmp/data.zip")

Documentation
-------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   configuration

.. toctree::
   :maxdepth: 2
   :caption: Core Modules

   api/core
   api/connectors
   api/medical

.. toctree::
   :maxdepth: 2
   :caption: Advanced Topics

   security
   hipaa-compliance
   cloud-connectors

.. toctree::
   :maxdepth: 1
   :caption: Reference

   changelog
   contributing


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

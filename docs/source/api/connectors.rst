Cloud Connectors
================

Secure Media Processor supports multiple cloud storage providers through a unified
connector interface.

Base Connector
--------------

All connectors inherit from the abstract CloudConnector base class.

.. automodule:: src.connectors.base_connector
   :members:
   :undoc-members:
   :show-inheritance:

AWS S3 Connector
----------------

.. automodule:: src.connectors.s3_connector
   :members:
   :undoc-members:
   :show-inheritance:

Azure Blob Storage Connector
----------------------------

.. automodule:: src.connectors.azure_blob_connector
   :members:
   :undoc-members:
   :show-inheritance:

Google Drive Connector
----------------------

.. automodule:: src.connectors.google_drive_connector
   :members:
   :undoc-members:
   :show-inheritance:

Dropbox Connector
-----------------

.. automodule:: src.connectors.dropbox_connector
   :members:
   :undoc-members:
   :show-inheritance:

OneDrive Connector
------------------

.. automodule:: src.connectors.onedrive_connector
   :members:
   :undoc-members:
   :show-inheritance:

Connector Manager
-----------------

The ConnectorManager allows you to work with multiple cloud providers simultaneously.

.. automodule:: src.connectors.connector_manager
   :members:
   :undoc-members:
   :show-inheritance:

Examples
--------

AWS S3
~~~~~~

.. code-block:: python

   from src.connectors import S3Connector

   connector = S3Connector(
       bucket_name="medical-data",
       region="us-east-1",
       access_key="AKIAIOSFODNN7EXAMPLE",
       secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
   )

   connector.connect()

   # Upload with encryption
   result = connector.upload_file(
       file_path="scan.dcm",
       remote_path="studies/patient123/scan.dcm",
       metadata={"study_type": "MRI"}
   )

   # Download with checksum verification
   result = connector.download_file(
       remote_path="studies/patient123/scan.dcm",
       local_path="/tmp/scan.dcm",
       verify_checksum=True
   )

   connector.disconnect()

Azure Blob Storage
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.connectors import AzureBlobConnector

   connector = AzureBlobConnector(
       container_name="medical-data",
       connection_string="DefaultEndpointsProtocol=https;AccountName=..."
   )

   connector.connect()

   # Upload
   connector.upload_file("local.dcm", "remote/path.dcm")

   # Generate temporary access URL
   result = connector.generate_sas_url(
       remote_path="remote/path.dcm",
       expiry_hours=24,
       read_only=True
   )
   print(result['sas_url'])

   connector.disconnect()

OneDrive
~~~~~~~~

.. code-block:: python

   from src.connectors import OneDriveConnector

   connector = OneDriveConnector(
       client_id="your-app-id",
       client_secret="your-secret",
       tenant_id="your-tenant-id"
   )

   connector.connect()

   # Upload
   connector.upload_file("report.pdf", "documents/report.pdf")

   # Create sharing link
   result = connector.create_sharing_link(
       remote_path="documents/report.pdf",
       link_type="view",
       expiry_hours=48
   )
   print(result['sharing_url'])

   connector.disconnect()

Using Multiple Connectors
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.connectors import ConnectorManager, S3Connector, AzureBlobConnector

   manager = ConnectorManager()

   # Add connectors
   manager.add_connector('aws', S3Connector(bucket_name="primary"))
   manager.add_connector('azure', AzureBlobConnector(
       container_name="backup",
       connection_string="..."
   ))

   # Connect all
   manager.connect_all()

   # Upload to specific connector
   manager.upload_file("data.zip", "backups/data.zip", connector_name="azure")

   # Upload to default (first) connector
   manager.upload_file("data.zip", "data.zip")

   manager.disconnect_all()

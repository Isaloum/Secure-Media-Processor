Cloud Connectors Guide
======================

Secure Media Processor supports multiple cloud storage providers through a unified
interface.

Supported Providers
-------------------

.. list-table::
   :header-rows: 1
   :widths: 20 30 25 25

   * - Provider
     - Connector Class
     - Install Extra
     - HIPAA BAA
   * - AWS S3
     - ``S3Connector``
     - (included)
     - Yes
   * - Azure Blob
     - ``AzureBlobConnector``
     - ``[azure]``
     - Yes
   * - Google Cloud
     - ``GoogleDriveConnector``
     - (included)
     - Yes
   * - Dropbox
     - ``DropboxConnector``
     - (included)
     - Business only
   * - OneDrive
     - ``OneDriveConnector``
     - ``[onedrive]``
     - Yes (M365)

AWS S3
------

Best for: Enterprise deployments, large-scale medical imaging

.. code-block:: python

   from src.connectors import S3Connector

   connector = S3Connector(
       bucket_name="medical-data",
       region="us-east-1",
       encryption="aws:kms"  # Use KMS for HIPAA
   )

Azure Blob Storage
------------------

Best for: Microsoft ecosystem, Azure-based healthcare platforms

.. code-block:: python

   from src.connectors import AzureBlobConnector

   connector = AzureBlobConnector(
       container_name="phi-data",
       connection_string="DefaultEndpointsProtocol=https;..."
   )

   # Generate temporary access URL
   sas_result = connector.generate_sas_url(
       remote_path="studies/study001.zip",
       expiry_hours=24
   )

Google Cloud Storage
--------------------

Best for: Google Cloud Platform deployments, BigQuery integration

.. code-block:: python

   from src.connectors import GoogleDriveConnector

   connector = GoogleDriveConnector(
       credentials_path="/path/to/credentials.json"
   )

OneDrive / SharePoint
---------------------

Best for: Microsoft 365 environments, document sharing

.. code-block:: python

   from src.connectors import OneDriveConnector

   connector = OneDriveConnector(
       client_id="your-app-id",
       client_secret="your-secret",
       tenant_id="your-tenant"
   )

   # Create sharing link
   link = connector.create_sharing_link(
       remote_path="reports/summary.pdf",
       link_type="view",
       expiry_hours=48
   )

Multi-Cloud Strategy
--------------------

Use ConnectorManager for multi-cloud deployments:

.. code-block:: python

   from src.connectors import ConnectorManager, S3Connector, AzureBlobConnector

   manager = ConnectorManager()

   # Primary storage
   manager.add_connector('primary', S3Connector(bucket_name="main"))

   # Backup storage
   manager.add_connector('backup', AzureBlobConnector(
       container_name="backup",
       connection_string="..."
   ))

   manager.connect_all()

   # Upload to both
   manager.upload_file("data.zip", "data.zip", connector_name="primary")
   manager.upload_file("data.zip", "data.zip", connector_name="backup")

Choosing a Provider
-------------------

Consider these factors:

1. **Compliance**: Does the provider offer a BAA?
2. **Location**: Data residency requirements
3. **Cost**: Storage and transfer costs
4. **Integration**: Existing infrastructure
5. **Performance**: Latency to your GPU servers

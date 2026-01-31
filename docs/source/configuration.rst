Configuration
=============

Secure Media Processor can be configured through environment variables, configuration
files, or programmatically.

Environment Variables
---------------------

Cloud Storage
~~~~~~~~~~~~~

AWS S3:

.. code-block:: bash

   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export AWS_REGION="us-east-1"
   export AWS_BUCKET_NAME="your-bucket"

Azure Blob Storage:

.. code-block:: bash

   export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
   export AZURE_CONTAINER_NAME="your-container"

Google Cloud:

.. code-block:: bash

   export GCP_PROJECT_ID="your-project"
   export GCP_BUCKET_NAME="your-bucket"
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"

Dropbox:

.. code-block:: bash

   export DROPBOX_ACCESS_TOKEN="your-token"

OneDrive:

.. code-block:: bash

   export ONEDRIVE_CLIENT_ID="your-client-id"
   export ONEDRIVE_CLIENT_SECRET="your-secret"
   export ONEDRIVE_TENANT_ID="your-tenant-id"

Processing Settings
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   export SMP_TEMP_DIR="/secure/temp"
   export SMP_KEYS_DIR="/secure/keys"
   export SMP_AUDIT_DIR="/secure/audit"
   export GPU_ENABLED="true"
   export BATCH_SIZE="32"
   export MAX_WORKERS="4"

Docker Configuration
--------------------

Using Docker Compose with environment file:

.. code-block:: bash

   # .env file
   AWS_ACCESS_KEY_ID=your-key
   AWS_SECRET_ACCESS_KEY=your-secret
   AZURE_STORAGE_CONNECTION_STRING=your-connection-string

   # Run with env file
   docker-compose --env-file .env up smp

Programmatic Configuration
--------------------------

.. code-block:: python

   from src.core import SecureTransferPipeline
   from src.connectors import S3Connector

   # Configure pipeline
   pipeline = SecureTransferPipeline(
       temp_dir="/custom/temp",
       key_dir="/custom/keys",
       secure_delete_passes=5
   )

   # Configure connector
   connector = S3Connector(
       bucket_name="my-bucket",
       region="eu-west-1",
       encryption="aws:kms"
   )

Security Best Practices
-----------------------

1. **Never commit credentials** - Use environment variables or secrets managers
2. **Rotate keys regularly** - Implement key rotation policies
3. **Use least privilege** - Grant minimal required permissions
4. **Enable audit logging** - Always log security-relevant events
5. **Secure temp directories** - Use encrypted filesystems for temporary storage

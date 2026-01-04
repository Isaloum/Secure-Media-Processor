---
name: Add New Cloud Provider
about: Propose adding a new cloud storage provider connector
title: '[PROVIDER] Add support for [Provider Name]'
labels: enhancement, good first issue, connector
assignees: ''

---

## 🌩️ Cloud Provider Information

**Provider Name:** [e.g., Azure Blob Storage, Backblaze B2, OneDrive]

**Provider Website:** [URL to provider's website]

**API Documentation:** [URL to provider's API documentation]

## 💡 Motivation

Why would this provider be valuable to users?

**Use Cases:**
1. Use case 1...
2. Use case 2...

**Target Users:**
- [ ] Individual users
- [ ] Small businesses
- [ ] Enterprise users
- [ ] Specific industry (please specify): _______________

## 🔧 Technical Information

**Official SDK/Library:**
- SDK Name: [e.g., azure-storage-blob]
- Package Manager: [e.g., pip install azure-storage-blob]
- SDK Documentation: [URL]
- License: [e.g., MIT, Apache 2.0]

**API Capabilities:**
- [ ] File upload
- [ ] File download
- [ ] File deletion
- [ ] File listing
- [ ] Metadata support
- [ ] Server-side encryption
- [ ] Checksum verification
- [ ] Versioning support
- [ ] Other: _______________

## 📋 Implementation Checklist

To implement this provider, the following tasks need to be completed:

- [ ] Research provider API and SDK
- [ ] Create `src/connectors/[provider]_connector.py` implementing `CloudConnector` interface
- [ ] Implement required methods:
  - [ ] `connect()` - Establish connection
  - [ ] `disconnect()` - Close connection
  - [ ] `upload_file()` - Upload files
  - [ ] `download_file()` - Download files with checksum verification
  - [ ] `delete_file()` - Delete files
  - [ ] `list_files()` - List files with prefix filter
  - [ ] `get_file_metadata()` - Retrieve file metadata
- [ ] Add logging throughout the connector
- [ ] Create comprehensive tests in `tests/test_[provider]_connector.py`
- [ ] Update `requirements.txt` with new SDK dependency
- [ ] Update `.env.example` with provider credentials template
- [ ] Update `README.md` with provider usage examples
- [ ] Add provider to `ConnectorManager` examples in documentation

## 🎨 Example Usage (Optional)

If you have an idea of how the connector should be used, please share it here:

```python
from src.connectors import ProviderConnector

# Initialize connector
connector = ProviderConnector(
    api_key='your-api-key',
    # other parameters
)

# Connect and use
connector.connect()
connector.upload_file('local.txt', 'remote/path.txt')
```

## 🔐 Authentication Requirements

**Credentials Needed:**
- [ ] API Key
- [ ] Access Token
- [ ] Service Account Credentials
- [ ] OAuth2 Flow
- [ ] Other: _______________

**Environment Variables:**
```bash
# Example from .env
PROVIDER_API_KEY=your_api_key
PROVIDER_REGION=us-east-1
# Add other required variables
```

## 📚 Additional Context

Add any other context, screenshots, code samples, or links about the feature request here.

## 🤝 Implementation Willingness

Are you willing to contribute to implementing this connector?

- [ ] Yes, I can implement it myself (we'll help you!)
- [ ] Yes, with guidance and code reviews
- [ ] I can help with testing
- [ ] I can help with documentation
- [ ] No, just suggesting the feature

## 📊 Priority

How important is this provider to you?

- [ ] Critical - Blocking my usage
- [ ] High - Very useful for my project
- [ ] Medium - Nice to have
- [ ] Low - Future enhancement

---

**Note for Contributors:**

This is marked as a `good first issue` because implementing a new cloud provider connector is a great way to contribute! The existing connectors (S3, Google Drive, Dropbox) serve as excellent reference implementations. The `CloudConnector` base class provides a clear interface to implement, making this task well-defined and achievable.

We provide support and guidance for all contributors. Don't hesitate to ask questions in the comments!

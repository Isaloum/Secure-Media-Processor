# PyPI Upload Instructions

Your package is built and ready to upload to PyPI!

## Package Information

**Built files:**
- `dist/secure_media_processor-1.0.0.tar.gz` (72 KB)
- `dist/secure_media_processor-1.0.0-py3-none-any.whl` (42 KB)

**What's included:**
- ✅ Universal GPU support (NVIDIA, Apple, AMD, Intel)
- ✅ Security hardening (path traversal, credential cleanup, rate limiting)
- ✅ License management system
- ✅ Multi-cloud storage (S3, Google Drive, Dropbox)
- ✅ AES-256-GCM encryption
- ✅ Comprehensive tests

## Step-by-Step Upload to PyPI

### 1. Create PyPI Account (if you don't have one)

Go to: https://pypi.org/account/register/

- Enter your email
- Verify email
- Set password

### 2. Create API Token

1. Log in to https://pypi.org/
2. Click your username → "Account settings"
3. Scroll to "API tokens"
4. Click "Add API token"
5. Name: `secure-media-processor`
6. Scope: "Entire account" (or create project first and scope to project)
7. **Copy the token** (starts with `pypi-...`)
8. **SAVE IT SOMEWHERE SAFE** - you can't see it again!

### 3. Upload to PyPI

```bash
cd /home/user/Secure-Media-Processor

# Upload using your API token
twine upload dist/* --username __token__ --password pypi-YOUR-API-TOKEN-HERE
```

**Example:**
```bash
twine upload dist/* --username __token__ --password pypi-AgEIcHlwaS5vcmcCJGFhYWFhYWFhLWJiYmItY2NjYy1kZGRkLWVlZWVlZWVlZWVlZQ
```

### 4. Verify Upload

After upload completes, check:

```bash
# Visit your package page
https://pypi.org/project/secure-media-processor/

# Test installation
pip install secure-media-processor

# Verify it works
smp --version
```

## Troubleshooting

### "Package already exists"

If you get this error, the package name is taken. Options:
1. Choose different name in `pyproject.toml` (e.g., `secure-media-processor-pro`)
2. Contact current package owner to transfer

### "Invalid credentials"

- Make sure you copied the full API token (starts with `pypi-`)
- Username must be exactly `__token__` (with double underscores)
- Check no extra spaces in token

### "Invalid distribution metadata"

The package has a minor metadata warning but should still upload fine. If PyPI rejects it:

```bash
# Fix by using text license format
# Edit pyproject.toml line 11:
# From: license = "MIT"
# To:   license = {text = "MIT"}

# Rebuild
rm -rf dist/ && python -m build

# Try upload again
twine upload dist/*
```

### "HTTPError: 403 Forbidden"

- Check you're using the right token
- Verify token has correct permissions
- Try creating a "project-scoped" token instead

## After Successful Upload

### 1. Update Website

Add PyPI badge to README and website:

```markdown
[![PyPI](https://img.shields.io/pypi/v/secure-media-processor)](https://pypi.org/project/secure-media-processor/)
[![Downloads](https://img.shields.io/pypi/dm/secure-media-processor)](https://pypi.org/project/secure-media-processor/)
```

### 2. Update Landing Page

Change installation instructions to:

```bash
# Now live on PyPI!
pip install secure-media-processor
```

### 3. Announce Launch

- Update `READY_TO_LAUNCH.md` - mark PyPI as ✅ complete
- Tweet/post: "Secure Media Processor is now on PyPI! Install with: pip install secure-media-processor"
- Update marketing materials with PyPI link

### 4. Monitor

Check these stats daily:
- PyPI downloads: https://pypistats.org/packages/secure-media-processor
- GitHub stars
- Issues/bug reports

## Test PyPI (Optional - For Practice)

Want to practice first? Use Test PyPI:

```bash
# 1. Create account at https://test.pypi.org/account/register/

# 2. Create API token at https://test.pypi.org/manage/account/

# 3. Upload to test PyPI
twine upload --repository testpypi dist/* --username __token__ --password YOUR-TEST-PYPI-TOKEN

# 4. Test installation
pip install --index-url https://test.pypi.org/simple/ secure-media-processor

# 5. If it works, upload to real PyPI (step 3 above)
```

## Package Versioning

For future updates:

1. Update version in `pyproject.toml` (e.g., `1.0.1`, `1.1.0`, `2.0.0`)
2. Rebuild: `rm -rf dist/ && python -m build`
3. Upload: `twine upload dist/*`

**Semantic versioning:**
- `1.0.x` - Bug fixes
- `1.x.0` - New features (backward compatible)
- `x.0.0` - Breaking changes

## Security Note

**Never commit API tokens to git!**

If you accidentally expose your token:
1. Go to https://pypi.org/manage/account/
2. Delete the compromised token
3. Create a new one

## Support

Need help? Check:
- PyPI guide: https://packaging.python.org/tutorials/packaging-projects/
- Twine docs: https://twine.readthedocs.io/
- Create GitHub issue: https://github.com/Isaloum/Secure-Media-Processor/issues

---

## Quick Command Reference

```bash
# Build package
python -m build

# Check package
twine check dist/*

# Upload to PyPI
twine upload dist/* --username __token__ --password YOUR-TOKEN

# Install and test
pip install secure-media-processor
smp --version
```

**You're ready to upload! Just need your PyPI API token.** 🚀

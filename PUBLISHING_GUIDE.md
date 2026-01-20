# Publishing to PyPI - Step-by-Step Guide

This guide will help you publish **Secure Media Processor** to PyPI so users can install it with `pip install secure-media-processor`.

---

## Prerequisites

1. **PyPI Account**
   - Go to https://pypi.org/account/register/
   - Create account with your email
   - Verify your email address

2. **Test PyPI Account** (optional but recommended)
   - Go to https://test.pypi.org/account/register/
   - Create account (can use same email)
   - This lets you test publishing first

3. **API Tokens**
   - After creating account, go to https://pypi.org/manage/account/token/
   - Click "Add API token"
   - Name: "secure-media-processor-upload"
   - Scope: "Entire account" (for first time)
   - Copy the token (starts with `pypi-...`)
   - **SAVE THIS TOKEN** - you'll only see it once!

---

## Step 1: Install Build Tools

```bash
cd /home/user/Secure-Media-Processor

# Install build tools
pip install --upgrade build twine
```

**Expected output:**
```
Successfully installed build-X.X.X twine-X.X.X
```

---

## Step 2: Build Distribution Files

```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info

# Build package
python -m build
```

**Expected output:**
```
Successfully built secure-media-processor-1.0.0.tar.gz and secure_media_processor-1.0.0-py3-none-any.whl
```

**What this creates:**
- `dist/secure-media-processor-1.0.0.tar.gz` - Source distribution
- `dist/secure_media_processor-1.0.0-py3-none-any.whl` - Wheel (binary)

---

## Step 3: Check Package (Important!)

```bash
# Verify package is correct
twine check dist/*
```

**Expected output:**
```
Checking dist/secure-media-processor-1.0.0.tar.gz: PASSED
Checking dist/secure_media_processor-1.0.0-py3-none-any.whl: PASSED
```

**If you see errors:**
- Fix the issues mentioned
- Rebuild with `python -m build`
- Check again

---

## Step 4: Test Install Locally (CRITICAL)

```bash
# Create test virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install your package locally
pip install dist/secure_media_processor-1.0.0-py3-none-any.whl

# Test it works
smp --version
smp license status

# Clean up
deactivate
rm -rf test_env
```

**Expected output:**
```
smp --version
# Should show: 1.0.0

smp license status
# Should show: Free tier message
```

---

## Step 5: Publish to Test PyPI (Recommended First Time)

```bash
# Upload to Test PyPI
twine upload --repository testpypi dist/*
```

**You'll be prompted:**
```
Enter your API token: pypi-...
```

**Paste your Test PyPI token**

**Expected output:**
```
Uploading distributions to https://test.pypi.org/legacy/
Uploading secure_media_processor-1.0.0-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 450.0/450.0 kB
Uploading secure-media-processor-1.0.0.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 380.0/380.0 kB

View at:
https://test.pypi.org/project/secure-media-processor/1.0.0/
```

**Test the installation:**
```bash
# In a new virtual environment
python -m venv test_install
source test_install/bin/activate

# Install from Test PyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ secure-media-processor

# Test it
smp --version

deactivate
rm -rf test_install
```

---

## Step 6: Publish to Real PyPI (GO LIVE!)

```bash
# Upload to production PyPI
twine upload dist/*
```

**You'll be prompted:**
```
Enter your API token: pypi-...
```

**Paste your PRODUCTION PyPI token**

**Expected output:**
```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading secure_media_processor-1.0.0-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 450.0/450.0 kB
Uploading secure-media-processor-1.0.0.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 380.0/380.0 kB

View at:
https://pypi.org/project/secure-media-processor/1.0.0/
```

---

## Step 7: Verify Live Package

```bash
# Wait 1-2 minutes for PyPI to process

# Test installation from PyPI
python -m venv verify_install
source verify_install/bin/activate

pip install secure-media-processor

# Test it works
smp --version
smp license status
smp --help

deactivate
rm -rf verify_install
```

---

## 🎉 YOU'RE LIVE!

Your package is now available to **anyone in the world**:

```bash
pip install secure-media-processor
```

**Share these links:**
- PyPI page: https://pypi.org/project/secure-media-processor/
- Install command: `pip install secure-media-processor`

---

## Troubleshooting

### "Package name already taken"
- Someone else has that name
- Change name in `pyproject.toml`: `name = "secure-media-processor-yourusername"`
- Rebuild and try again

### "Invalid credentials"
- Make sure you're using API token, not password
- Token should start with `pypi-`
- Generate new token if needed

### "File already exists"
- You can't overwrite published versions
- Increase version in `pyproject.toml`: `version = "1.0.1"`
- Rebuild and republish

### "Dependency errors on install"
- Some dependencies are large (torch, opencv)
- Users may need to install separately
- Document in README

---

## Version Updates

When you make changes and want to publish an update:

1. **Update version** in `pyproject.toml`:
   ```toml
   version = "1.0.1"  # Increment patch version
   ```

2. **Clean and rebuild**:
   ```bash
   rm -rf dist/ build/ *.egg-info
   python -m build
   ```

3. **Check**:
   ```bash
   twine check dist/*
   ```

4. **Upload**:
   ```bash
   twine upload dist/*
   ```

**Versioning Guidelines:**
- Patch (1.0.0 → 1.0.1): Bug fixes
- Minor (1.0.0 → 1.1.0): New features, backward compatible
- Major (1.0.0 → 2.0.0): Breaking changes

---

## Security Best Practices

1. **Never commit API tokens** to git
2. **Use API tokens**, not passwords
3. **Scope tokens** to specific projects after first upload
4. **Store tokens** in password manager
5. **Revoke old tokens** when done

---

## After Publishing

1. **Update README** with install instructions
2. **Create GitHub release** matching version
3. **Announce on Twitter/LinkedIn**
4. **Submit to Python Weekly**
5. **Post on r/Python subreddit**

---

## Marketing Your Package

**GitHub:**
- Add PyPI badge to README
- Tag release with version number
- Update documentation

**Social Media:**
- "Just published X to PyPI!"
- Share install command
- Highlight key features

**Reddit:**
- r/Python (no self-promotion day rules)
- r/programming
- r/SideProject

**Hacker News:**
- "Show HN: Secure Media Processor - Privacy-focused media processing"
- Include PyPI link

---

## Next Steps

1. ✅ Publish to PyPI (you're here!)
2. Create sales page for Pro licenses
3. Set up Gumroad/Stripe for payments
4. Generate license keys for customers
5. Launch marketing campaign

**Estimated time to first sale: 2-3 days**

---

## Need Help?

- PyPI Help: https://pypi.org/help/
- Packaging Guide: https://packaging.python.org/tutorials/packaging-projects/
- This repo issues: https://github.com/Isaloum/Secure-Media-Processor/issues

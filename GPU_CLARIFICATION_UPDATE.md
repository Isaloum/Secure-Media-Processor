# GPU Support Clarification - Manual Update Required

## What Was Updated

The GPU references have been clarified to specify **NVIDIA CUDA GPU support only** to prevent user confusion.

## Changes Needed on GitHub Pages

You need to manually update the following files on the `gh-pages` branch via GitHub UI:

### 1. Update `_config.yml`

**Change line 3 from:**
```yaml
description: Military-grade encryption meets GPU acceleration for your media files
```

**To:**
```yaml
description: Military-grade encryption meets NVIDIA CUDA GPU acceleration for your media files
```

### 2. Update `index.md`

**Make these changes:**

**A) Line 4 - Update description:**
```yaml
description: Military-grade encryption meets NVIDIA CUDA GPU acceleration for your media files
```

**B) Lines 49-57 - Update GPU Acceleration section:**
```html
<div style="padding: 25px; border: 2px solid #667eea; border-radius: 12px; background: #f8f9ff;">
  <h3>⚡ NVIDIA CUDA GPU Acceleration</h3>
  <p>Blazing-fast image processing powered by NVIDIA CUDA. Resize, filter, and transform images at incredible speeds on RTX/Tesla GPUs.</p>
  <ul>
    <li>✓ NVIDIA GPU support (RTX 20/30/40, Tesla, A100)</li>
    <li>✓ Automatic CPU fallback</li>
    <li>✓ Batch processing</li>
  </ul>
</div>
```

**C) After line 109 - Add GPU Requirements section:**
```markdown
### GPU Requirements (Optional)

For GPU-accelerated image processing, you'll need:

- **NVIDIA GPU** with CUDA support (RTX 20/30/40 series, Tesla, A100, etc.)
- **CUDA drivers** installed on your system
- **PyTorch with CUDA** enabled

> **Note:** AMD GPUs, Intel Arc, and Apple M1/M2/M3 are not currently supported. The software automatically falls back to CPU processing if no NVIDIA GPU is detected.
```

**D) Line 129 - Update:**
```markdown
**4. NVIDIA CUDA GPU-accelerated image processing:**
```

**E) Line 162 - Update:**
```markdown
- **⚡ Performance**: NVIDIA CUDA GPU acceleration delivers professional-grade processing speeds (CPU fallback included)
```

## Why This Matters

**Current issue:** The website says "GPU acceleration" generically, which is misleading.

**Reality:** Only NVIDIA GPUs with CUDA are supported. AMD GPUs, Intel Arc, and Apple Silicon (M1/M2/M3) will NOT work.

**Solution:** Be specific about NVIDIA CUDA requirement to set accurate expectations.

## How to Apply These Changes

1. Go to: https://github.com/Isaloum/Secure-Media-Processor/tree/gh-pages
2. Edit `_config.yml` - update line 3
3. Edit `index.md` - make the 5 changes listed above (A-E)
4. Commit both files
5. Wait 1-2 minutes for GitHub Pages to rebuild
6. Hard refresh: Cmd + Shift + R

## Expected Result

After updating, the website will clearly state:
- ✅ "NVIDIA CUDA GPU acceleration" (not generic "GPU")
- ✅ Supported GPUs: RTX 20/30/40, Tesla, A100
- ✅ Unsupported: AMD, Intel Arc, Apple M1/M2/M3
- ✅ Automatic CPU fallback included

This sets accurate expectations and prevents user confusion.

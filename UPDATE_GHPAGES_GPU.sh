#!/bin/bash
# Manual update script for GitHub Pages universal GPU support

echo "To manually update GitHub Pages for universal GPU support:"
echo ""
echo "1. Go to: https://github.com/Isaloum/Secure-Media-Processor/blob/gh-pages/_config.yml"
echo "2. Click pencil icon to edit"
echo "3. Change line 3 to:"
echo "   description: Universal GPU acceleration - works with NVIDIA, Apple, AMD, and Intel GPUs"
echo ""
echo "4. Go to: https://github.com/Isaloum/Secure-Media-Processor/blob/gh-pages/index.md"
echo "5. Click pencil icon to edit"
echo "6. Change line 4 to:"
echo "   description: Universal GPU acceleration - works with NVIDIA, Apple, AMD, and Intel GPUs"
echo ""
echo "7. Find the GPU Acceleration section (around line 50) and replace with:"
echo ""
cat << 'EOF'
<div style="padding: 25px; border: 2px solid #667eea; border-radius: 12px; background: #f8f9ff;">
  <h3>⚡ Universal GPU Acceleration</h3>
  <p>Works with ANY GPU - NVIDIA (RTX/Tesla), Apple (M1/M2/M3), AMD (Radeon), Intel (Arc). Automatic detection and CPU fallback.</p>
  <ul>
    <li>✓ NVIDIA CUDA (RTX 20/30/40, Tesla)</li>
    <li>✓ Apple Metal (M1/M2/M3 Macs)</li>
    <li>✓ AMD ROCm + Intel Arc support</li>
  </ul>
</div>
EOF
echo ""
echo "8. Commit changes"
echo "9. Wait 1-2 minutes for rebuild"
echo "10. Hard refresh: Cmd + Shift + R"

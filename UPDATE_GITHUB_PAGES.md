# Update GitHub Pages - CRITICAL FIX

## Problem Identified

The `jekyll-theme-cayman` theme has built-in CSS that **overrides inline styles**. That's why the hero section wasn't updating even though the index.md had correct values.

## Solution

Created `assets/css/style.scss` with `!important` declarations to force the theme to use our smaller hero section.

## Files to Deploy

1. `index.md` - Updated hero section HTML
2. `assets/css/style.scss` - Custom CSS overrides for Cayman theme

## Deploy Instructions

```bash
# 1. Copy files to gh-pages branch
git checkout gh-pages
git checkout main -- index.md assets/css/style.scss
git add index.md assets/css/style.scss
git commit -m "Fix: Override Cayman theme CSS for smaller hero section"

# 2. Push to GitHub (you'll need to do this manually)
git push origin gh-pages

# 3. Switch back to main
git checkout main
```

## Manual Deploy via GitHub UI

If push fails due to branch protection:

1. Go to: https://github.com/Isaloum/Secure-Media-Processor
2. Switch to `gh-pages` branch
3. Click on `assets/css/style.scss` (or create it)
4. Add this content:

```scss
---
---

@import "{{ site.theme }}";

/* Override Cayman theme's hero section with reduced sizes */
.page-header {
  padding: 50px 20px !important;
}

.page-header .project-name {
  font-size: 2.2rem !important;
  margin-bottom: 20px !important;
}

.page-header .project-tagline {
  font-size: 1.1rem !important;
  margin-top: 20px !important;
}

/* Override for custom hero div if it exists */
div[align="center"] h1 {
  font-size: 2.2em !important;
}

div[align="center"] > div[style*="padding"] {
  padding: 50px 20px !important;
}

div[align="center"] p {
  font-size: 1.1em !important;
}
```

5. Commit the file
6. Wait 1-2 minutes for GitHub Pages to rebuild
7. Hard refresh browser: Cmd+Shift+R

## Why This Works

Jekyll processes `.scss` files and the `!important` declarations override the theme's default CSS.

The website will update within 1-2 minutes after the CSS file is deployed.

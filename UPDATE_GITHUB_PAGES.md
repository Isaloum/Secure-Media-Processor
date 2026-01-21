# Update GitHub Pages

The live website at https://isaloum.github.io/Secure-Media-Processor/ is served from the `gh-pages` branch.

## Hero Section Updated

The hero section has been reduced to match Copilot's UI changes:
- **Padding:** 60px → 50px (more compact)
- **Heading size:** 3.5em → 2.2em (smaller, cleaner)
- **Subtitle size:** 1.4em → 1.1em (more balanced)

## To Deploy the Updated UI

The updated `index.md` file is included in this branch. To deploy it to GitHub Pages:

```bash
# 1. Merge this PR to main
# (done via GitHub UI)

# 2. Update gh-pages branch with new index.md
git checkout gh-pages
git checkout main -- index.md
git commit -m "UI: Reduce hero section size"
git push origin gh-pages

# 3. GitHub Pages will rebuild automatically (takes 1-2 minutes)
```

## Or Quick Update

```bash
# Quick one-liner to update gh-pages
git fetch origin && \
git checkout gh-pages && \
git checkout origin/claude/setup-production-fullstack-NWyrz -- index.md && \
git commit -m "UI: Update hero section from PR #18" && \
git push origin gh-pages && \
git checkout main
```

The website will update within 1-2 minutes after pushing to gh-pages.

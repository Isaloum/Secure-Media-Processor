# Gumroad Setup - Quick Start (10 Minutes)

## Step 1: Create Account (2 min)

1. Go to https://gumroad.com
2. Click "Start Selling"
3. Sign up with your email
4. Verify your email

## Step 2: Create Pro Product (3 min)

1. Click "+" to create new product
2. **Product Name:** Secure Media Processor Pro
3. **Description:**
```
Privacy-focused media processing with GPU acceleration.

What you get:
✓ AWS S3, Google Drive, Dropbox connectors
✓ GPU-accelerated processing (10x faster)
✓ Batch operations
✓ Email support
✓ 1 device activation
✓ AES-256-GCM encryption
✓ Zero-knowledge security

License delivered via email instantly.
30-day money-back guarantee.

Installation: pip install secure-media-processor
```

4. **Price:** $199
5. **Type:** Digital product
6. **Content:** "License key will be sent via email"

7. **Customize:**
   - Add cover image (1200x630 recommended)
   - Enable "Send product to customer via email"

8. Click "Save"

## Step 3: Create Enterprise Product (2 min)

Same as above but:
- **Product Name:** Secure Media Processor Enterprise
- **Price:** $2,999
- **Description:** Add:
```
Everything in Pro, plus:
✓ Multi-cloud sync between providers
✓ Priority support (24h response)
✓ 5 device activations
✓ Custom encryption keys
✓ Training & onboarding
✓ SLA guarantee
```

## Step 4: Set Up Email Automation (2 min)

For each product:

1. Go to product settings
2. Click "Email"
3. **Subject:** Your Secure Media Processor Pro License 🔑
4. **Body:** (Use template from `marketing/EMAIL_TEMPLATES.md`)

```
Hi {customer_name},

Thank you for upgrading to Secure Media Processor Pro!

Your license information:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LICENSE KEY: [WILL GENERATE AND ADD MANUALLY]
Email: {customer_email}
Type: PRO
Valid For: 365 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ACTIVATION INSTRUCTIONS:

Step 1: Install
pip install secure-media-processor

Step 2: Activate
smp license activate [YOUR-KEY]

Step 3: Enter email when prompted
{customer_email}

Need help? Reply to this email!

Best regards,
[Your Name]
```

5. Save

## Step 5: Test Purchase (1 min)

1. Click "Preview" on your product
2. Copy the product URL
3. Save it for your landing page
4. (Optional) Make a test purchase to verify email works

## Step 6: Handle First Customer

When someone buys:

1. You'll get email notification
2. Run: `python scripts/generate_license.py customer@email.com PRO 365`
3. Copy the generated license key
4. Go to Gumroad dashboard
5. Find the sale
6. Click "Edit" on the automated email
7. Replace `[WILL GENERATE AND ADD MANUALLY]` with actual key
8. Click "Resend email"

## Alternative: Automate with Webhooks (Advanced)

If you get >10 sales/day, set up webhook:

1. Create simple backend (Flask/FastAPI)
2. Endpoint generates license key automatically
3. Sends custom email with key
4. Configure in Gumroad Settings → Advanced → Webhooks

(This is optional - manual works fine for starting out)

---

## Update Your Landing Page

Replace in `landing_page.html`:

```html
<!-- Find this line -->
<a href="https://gum.co/YOUR-PRODUCT-HERE" class="cta-button">Upgrade to Pro</a>

<!-- Replace with your actual Gumroad URL -->
<a href="https://gumroad.com/l/YOUR-PRODUCT-ID" class="cta-button">Upgrade to Pro</a>
```

Do this for all CTA buttons.

---

## Gumroad vs Stripe

**Use Gumroad if:**
- ✅ Want to launch TODAY
- ✅ Don't want to handle taxes
- ✅ Don't want to build payment forms
- ✅ Okay with 10% + payment fees

**Use Stripe if:**
- ✅ Want lower fees (2.9% + 30¢)
- ✅ Can build checkout flow
- ✅ Want more control
- ✅ Have time to set up

**My recommendation: Start with Gumroad, switch to Stripe at $10k MRR.**

---

## Your Gumroad URLs

After setup, you'll have:

**Pro:** https://gumroad.com/l/secure-media-pro
**Enterprise:** https://gumroad.com/l/secure-media-enterprise

Update these in:
- `landing_page.html`
- `marketing/SALES_PAGE_COPY.md`
- All social media posts

---

## Tips

1. **Enable affiliate program** - 20% commission attracts promoters
2. **Offer payment plans** - $19/month option increases conversions
3. **Add upsells** - Offer Enterprise upgrade after Pro purchase
4. **Track metrics** - Sales, conversion rate, refunds
5. **Respond fast** - Answer support emails < 24h

---

## Total Time: ~10 minutes

You're ready to sell! 🚀

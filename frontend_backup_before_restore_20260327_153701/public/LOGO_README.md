# How to Add Your Logo

## ⚠️ Important: Replace the placeholder logo

The current `logo.png` is just a temporary SVG placeholder.

## Steps to add your real logo:

1. **Save your logo image** (the trading chart logo from the image you provided) as `logo.png`

2. **Copy it to this folder**:
   ```
   fx-alpha-platform/frontend/public/logo.png
   ```

3. **Recommended logo specifications**:
   - Format: PNG with transparent background
   - Size: 200x200px or larger (will auto-scale)
   - Aspect ratio: Keep the original ratio
   - File name: Must be exactly `logo.png`

4. **After copying the logo**:
   - The changes will be reflected immediately (Hot Module Replacement)
   - No need to restart the dev server

## Current usage of logo:

The logo is used in:
- Landing page (`/`)
- Login page (`/login`)
- Register page (`/register`)
- Sidebar navigation (dashboard)

All references use: `<img src="/logo.png" alt="Trady" className="h-10 w-auto" />`

The logo will automatically scale to the correct size while maintaining its aspect ratio.

# Putting this on your GitHub (5 minutes, no git required)

Do this on any computer — your regular laptop is easiest. Your
username is already baked into every file, so this is purely
drag-and-drop.

## 1. Create the empty repository

1. Go to **github.com** and sign in as **zlipson1999**.
2. Click the **+** in the top-right corner -> **New repository**.
3. Repository name: **atom-pi** (exactly this — the install
   command depends on it)
4. Set it to **Public** (the Pi downloads from it without logging
   in — public makes that work with zero setup).
5. Do NOT tick "Add a README" — leave everything unticked.
6. Click **Create repository**.

## 2. Upload the files

1. On the page that appears, click the link that says
   **"uploading an existing file."**
2. Unzip the `atom-pi.zip` you downloaded from Claude.
3. Drag the **contents** of the atom-pi folder into the browser
   window — `install.sh`, `README.md`, this file, and the `merged/`
   and `patches/` folders. (Drag the items, not the outer folder —
   GitHub keeps the folder structure automatically.)
4. In the "Commit changes" box at the bottom, click
   **Commit changes**.

## 3. That's it

Your one-liner is live. On the Pi:

```
curl -fsSL https://raw.githubusercontent.com/zlipson1999/atom-pi/main/install.sh | bash
```

Any time Claude gives you updated files, repeat step 2 — dragging a
file with the same name replaces the old one.

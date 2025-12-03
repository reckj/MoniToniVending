# GitHub Repository Setup Instructions

Since GitHub CLI is not installed, please follow these steps to create and sync the repository:

## Step 1: Create Repository on GitHub

1. Go to: https://github.com/new
2. Fill in the details:
   - **Repository name**: `MoniToniVending`
   - **Description**: `Production-ready vending machine control system for Raspberry Pi 5`
   - **Visibility**: Public (or Private if you prefer)
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)

3. Click "Create repository"

## Step 2: Connect Local Repository

After creating the repository on GitHub, run these commands:

```bash
cd /home/selecta/PiToni

# Add GitHub as remote
git remote add origin https://github.com/reckj/MoniToniVending.git

# Push code to GitHub
git push -u origin main
```

## Step 3: Verify

Visit your repository at: https://github.com/reckj/MoniToniVending

You should see all your code and documentation!

---

## Alternative: Using SSH (Recommended for frequent pushes)

If you have SSH keys set up with GitHub:

```bash
cd /home/selecta/PiToni

# Add GitHub as remote (SSH)
git remote add origin git@github.com:reckj/MoniToniVending.git

# Push code to GitHub
git push -u origin main
```

---

## Troubleshooting

### If you get "remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/reckj/MoniToniVending.git
git push -u origin main
```

### If you need to set up SSH keys
1. Generate key: `ssh-keygen -t ed25519 -C "your_email@example.com"`
2. Add to GitHub: https://github.com/settings/keys
3. Copy public key: `cat ~/.ssh/id_ed25519.pub`

---

Once the repository is synced, let me know and I'll continue with the UI development!

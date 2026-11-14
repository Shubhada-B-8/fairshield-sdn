# GitHub Push Guide — FairShield-SDN V1

## Before you push

1. Create a **Private** repository on GitHub (for example, `fairshield-sdn-v1`). Do not initialize it with a README, license, or `.gitignore`, because this project already contains them.
2. Keep it private until your supervisor/institution has clarified IP ownership and disclosure requirements. The project currently contains an MIT license file; ask your institution before making the repository public.
3. Download `FairShield_SDN_V1.1.0_Complete_Release.zip` into Windows Downloads. Do not overwrite your existing working folder.
4. Open Ubuntu/WSL and extract this release into a new folder. These commands use the Windows Downloads path used in this project session:

```bash
mkdir -p ~/projects/fairshield_sdn_v1_release
unzip -q "/mnt/c/Users/Shubhada Benurkar/Downloads/FairShield_SDN_V1.1.0_Complete_Release.zip" -d ~/projects/fairshield_sdn_v1_release
cd ~/projects/fairshield_sdn_v1_release/FairShield-SDN-V1.1.0

# Check that this is the right folder
pwd
ls
```

If you saved the ZIP somewhere else, adjust only the path to the ZIP.

## Commands (run from the repository root)

```bash
# You should already be in ~/projects/fairshield_sdn_v1_release/FairShield-SDN-V1.1.0

# Initialize Git and inspect what will be committed
git init
git status --short

# Stage and inspect the staged file list
git add .
git status --short

# Commit the frozen V1 release
git commit -m "Release FairShield-SDN V1.1.0"
git branch -M main

# Replace the placeholders with your own GitHub username and private repo name
git remote add origin https://github.com/YOUR-USERNAME/fairshield-sdn-v1.git
git push -u origin main
```

Git will ask you to authenticate. Follow GitHub's browser/device sign-in or use a supported credential manager. Do not paste a personal access token into this document, terminal screenshots, or chat.

## If Git asks for your identity

Set the name and email you want attached to commits (prefer the email configured in your GitHub account):

```bash
git config --global user.name "Your Name"
git config --global user.email "YOUR_GITHUB_EMAIL"
```

Then repeat the commit and push commands.

## If `origin` already exists

Check it first:

```bash
git remote -v
```

If it points to the wrong repository, update it (replace the URL):

```bash
git remote set-url origin https://github.com/YOUR-USERNAME/fairshield-sdn-v1.git
git push -u origin main
```

## Verify the push

```bash
git status
git log -1 --oneline
git remote -v
```

Then open the private repository page on GitHub and confirm that README, `src/`, `tests/`, `docs/`, `paper/`, `presentation/`, `outputs/` and `mininet/` are visible.

## Important safety checks

- `.venv/`, Python caches, local logs, generated package metadata and local model binaries are excluded by `.gitignore`.
- Never commit passwords, API keys, tokens, personal credentials, or unrelated private files.
- Do not include WSL virtual environments or system files.
- Keep V1 stable. Develop V2 separately, for example on a branch named `v2-research`, after creating a V1 tag.

Optional release tag after the V1 push:

```bash
git tag -a v1.1.0 -m "Frozen FairShield-SDN V1.1.0"
git push origin v1.1.0
```

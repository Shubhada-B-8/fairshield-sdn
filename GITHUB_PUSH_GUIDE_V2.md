# GitHub Push Guide — FairShield-SDN V2.0.0

## Before pushing

- Keep the repository **private** until your institution has clarified IP ownership and disclosure rules.
- Do not commit `.venv`, API keys, passwords, access tokens, personal data or local machine logs.
- The V1.1.0 complete release archive is preserved in `releases/`.
- This guide prepares commands; it does not create or push a repository on your behalf.

## 1. Create a private GitHub repository

On GitHub, create an empty private repository named `fairshield-sdn`. Do not initialize it with a README, license or `.gitignore` because those files are already in this package.

## 2. Extract the V2 package in WSL

Assuming the ZIP is in Windows Downloads:

```bash
mkdir -p ~/projects/fairshield_sdn_v2_release
unzip -q "/mnt/c/Users/Shubhada Benurkar/Downloads/FairShield_SDN_V2.0.0_Complete_Release.zip" -d ~/projects/fairshield_sdn_v2_release
cd ~/projects/fairshield_sdn_v2_release/FairShield-SDN-V2.0.0
```

If you extracted it to a different location, change only the `cd` path.

## 3. Verify before committing

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m unittest discover -s tests -v
python -m fairshield.cli adaptive-demo --scenario all --windows 30 --seed 7 --capacity 500 --out outputs_v2_recheck
```

Review `git status` before staging.

## 4. Initialize and push V2

Replace `YOUR-GITHUB-USERNAME` with your GitHub username:

```bash
git init
git add .
git status --short
git commit -m "Release FairShield-SDN V2.0.0"
git branch -M main
git remote add origin https://github.com/YOUR-GITHUB-USERNAME/fairshield-sdn.git
git push -u origin main
git tag -a v2.0.0 -m "FairShield-SDN V2.0.0 research prototype"
git push origin v2.0.0
```

Follow GitHub's authentication flow. Do not paste a personal access token into chat or save it in the repository.

## 5. Preserve V1

The prior V1.1.0 release archive is included at:

`releases/FairShield_SDN_V1.1.0_Complete_Release.zip`

Do not overwrite this file. If you already have a V1 Git history elsewhere, retain its V1.1.0 tag in that repository. Do not create a V1.1.0 Git tag pointing to the V2 commit.

## 6. Recommended repository settings

- Keep visibility private until IP and institution approvals are clear.
- Enable branch protection after the first push if working with collaborators.
- Use GitHub Releases for the ZIP only after checking institution disclosure rules.
- Store large future datasets/checkpoints outside Git unless the license and repository policy permit them.

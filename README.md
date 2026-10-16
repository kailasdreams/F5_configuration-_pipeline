# Git-to-F5 BIG-IP Pipeline (VIP, Pool, Node)

Starter GitOps repository for managing F5 BIG-IP LTM nodes, pools/members, and virtual servers from YAML.

## Repository
- `config/f5-config.yaml` — desired LTM configuration
- `scripts/validate.py` — validates YAML and references
- `scripts/deploy.py` — deploys through the BIG-IP REST API
- `.github/workflows/f5-pipeline.yml` — GitHub Actions pipeline

## Quick start
1. Edit `config/f5-config.yaml` and replace sample documentation IPs with valid lab addresses.
2. Push this repository to GitHub.
3. Add repository/environment secrets `F5_HOST`, `F5_USERNAME`, and `F5_PASSWORD`.
4. Create a GitHub environment named `production` and configure required reviewers before using deployment.
5. Ensure the runner can reach the BIG-IP management interface and that the automation account has suitable LTM permissions.

Local validation (Python 3.10+):
```bash
pip install -r requirements.txt
python scripts/validate.py
```

Local deployment:
```bash
# Set F5_HOST, F5_USERNAME, F5_PASSWORD in your shell first.
python scripts/deploy.py --config config/f5-config.yaml
```

TLS verification is enabled by default. Keep it enabled and install a trusted management certificate where possible. `F5_VERIFY_TLS=false` exists for isolated labs with self-signed certificates only and weakens security.

## Pipeline behavior
- Pull request: validation only; no device changes.
- Push to `main`: validate, then deploy via the protected `production` environment.
- Manual run: GitHub Actions `workflow_dispatch`.

## Important
Test on a non-production BIG-IP first. This starter does not back up or roll back configuration, and it does not configure SSL certificates, client/server SSL profiles, route domains, advanced monitors, iRules, policies, HA failover, or AS3. HTTPS VIPs typically need a valid client SSL profile. The code supports `/Common` only. Verify REST API behavior against your TMOS version and use your normal change-approval process.

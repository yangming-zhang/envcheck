# envcheck

Validate `.env` files against a template. Zero dependencies — pure Python stdlib.

Never deploy with missing environment variables again.

## Install

```bash
curl -O https://raw.githubusercontent.com/yangming-zhang/envcheck/main/envcheck.py
python envcheck.py --help
```

## Commands

| Command | Description |
|---------|-------------|
| `check` | Check `.env` against a template (`.env.example`) |
| `diff`  | Diff two `.env` files side by side |
| `list`  | List all keys in a `.env` file |
| `lint`  | Lint `.env` file for formatting issues |

## Usage

```bash
# Check .env against .env.example (default paths)
python envcheck.py check

# Check custom paths
python envcheck.py check .env.production .env.example

# Show keys present in .env but not in template
python envcheck.py check --show-extra

# Diff two env files
python envcheck.py diff .env .env.staging

# List all keys (hide values for safety)
python envcheck.py list .env

# Lint for formatting issues
python envcheck.py lint .env
```

## Example output

```
  envcheck  .env  vs  .env.example

  ✓ 12 keys present and set
  ! 2 keys present but empty:
      DATABASE_PASSWORD
      REDIS_URL
  ✗ 3 keys missing from .env:
      STRIPE_SECRET_KEY  (example: 'sk_test_...')
      S3_BUCKET
      SENTRY_DSN
```

Exit code is `0` on success, `1` if any keys are missing or empty.

## CI/CD integration

```yaml
# GitHub Actions
- name: Check env
  run: python envcheck.py check .env.ci .env.example
```

```bash
# Pre-deploy hook
python envcheck.py check .env .env.example || exit 1
```

## Requirements

- Python 3.9+
- No third-party packages

## License

MIT

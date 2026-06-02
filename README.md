# envcheck

Check your `.env` file before it blows up in production.

```
$ python envcheck.py check

  envcheck  .env  ←→  .env.example

  ✓ 14 key(s) present and set
  ! 1 key(s) set to empty:
      REDIS_URL
  ✗ 2 key(s) missing from .env:
      STRIPE_SECRET_KEY  # e.g. sk_live_...
      SENTRY_DSN
```

Exit code is `0` when everything's set, `1` if anything is missing or empty — so it works as a pre-deploy gate.

## Setup

```bash
curl -O https://raw.githubusercontent.com/yangming-zhang/envcheck/main/envcheck.py
python envcheck.py --help
```

Python 3.9+, zero dependencies.

## Commands

```
check   validate .env against a template
diff    compare two .env files
list    show all keys (and whether they're set)
lint    catch formatting problems
```

## Usage

```bash
# Check .env against .env.example (default)
python envcheck.py check

# Custom paths
python envcheck.py check .env.production .env.example

# Also show keys that are in .env but not in the template
python envcheck.py check --show-extra

# What changed between two environments?
python envcheck.py diff .env.staging .env.production

# Careful: this prints the actual values
python envcheck.py diff .env .env.backup --show-values

# What keys are set? (values hidden)
python envcheck.py list .env

# Find formatting issues
python envcheck.py lint .env
```

## CI/CD

```yaml
# GitHub Actions
- name: Validate env
  run: python envcheck.py check .env.ci .env.example
```

```bash
# Pre-deploy check
python envcheck.py check || { echo "fix your .env first"; exit 1; }
```

## What `lint` catches

- Keys that don't match `[A-Za-z_][A-Za-z0-9_]*`
- Lines with no `=` sign
- Spaces inside key names
- Unmatched quotes in values

## Notes

- Handles `export FOO=bar` syntax (common in sourced shell files)
- Strips inline comments: `FOO=bar  # this part is ignored`
- Values don't need to be quoted, but single and double quotes are both supported
- A key with no value at all (just `KEY` with no `=`) is treated as `None`, not empty string

## License

MIT

#!/usr/bin/env python3
"""
envcheck - validate .env files before they bite you in production

    envcheck check                     # .env vs .env.example
    envcheck check .env.prod           # custom file
    envcheck diff .env .env.staging    # compare two files
    envcheck lint .env                 # formatting issues
    envcheck list .env                 # show all keys
"""

import sys
import os
import re
import argparse
from pathlib import Path


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

def parse_env(path: str) -> "dict[str, str | None]":
    """
    Parse a .env file into {key: value}.

    - Strips surrounding quotes (single or double)
    - Skips blank lines and # comments
    - value is None if the line is just KEY with no = sign
    """
    result: dict[str, str | None] = {}
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        # handle   export FOO=bar   (common in bash-sourced files)
        line = re.sub(r"^export\s+", "", line)

        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)(?:=(.*))?$", line)
        if not m:
            print(f"  warn: {path}:{lineno}: skipping malformed line: {raw!r}",
                  file=sys.stderr)
            continue

        key, val = m.group(1), m.group(2)
        if val is not None:
            val = val.strip()
            # strip matching quotes
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                val = val[1:-1]
            # inline comment:  FOO=bar  # comment
            # only strip if not inside quotes (we already stripped quotes above)
            val = re.sub(r"\s+#.*$", "", val)

        result[key] = val

    return result


# ---------------------------------------------------------------------------
# output helpers
# ---------------------------------------------------------------------------

_COLORS = {
    "red":    "\033[31m",
    "green":  "\033[32m",
    "yellow": "\033[33m",
    "cyan":   "\033[36m",
    "bold":   "\033[1m",
    "reset":  "\033[0m",
}

def _c(text: str, *codes: str) -> str:
    if not sys.stdout.isatty():
        return text
    prefix = "".join(_COLORS.get(c, "") for c in codes)
    return f"{prefix}{text}{_COLORS['reset']}"


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_check(args):
    env  = parse_env(args.env)
    tmpl = parse_env(args.template)

    if not tmpl and not Path(args.template).exists():
        sys.exit(f"template not found: {args.template}")

    missing = [k for k in tmpl if k not in env]
    empty   = [k for k in tmpl if k in env and (env[k] == "" or env[k] is None)]
    extra   = [k for k in env  if k not in tmpl]
    ok      = [k for k in tmpl if k in env and env[k]]

    label = _c("envcheck", "bold")
    print(f"\n  {label}  {args.env}  ←→  {args.template}\n")
    print(f"  {_c('✓', 'green')} {len(ok)} key(s) present and set")

    if empty:
        print(f"  {_c('!', 'yellow')} {len(empty)} key(s) set to empty:")
        for k in empty:
            example = tmpl.get(k)
            hint = f"  # e.g. {example}" if example else ""
            print(f"      {_c(k, 'yellow')}{hint}")

    if missing:
        print(f"  {_c('✗', 'red')} {len(missing)} key(s) missing from {args.env}:")
        for k in missing:
            example = tmpl.get(k)
            hint = f"  # e.g. {example}" if example else ""
            print(f"      {_c(k, 'red')}{hint}")

    if extra and args.show_extra:
        print(f"  {_c('?', 'cyan')} {len(extra)} extra key(s) not in template:")
        for k in extra:
            print(f"      {_c(k, 'cyan')}")

    print()

    if missing or empty:
        sys.exit(1)

    print(f"  {_c('All required keys are set.', 'green', 'bold')}\n")


def cmd_diff(args):
    a = parse_env(args.a)
    b = parse_env(args.b)

    only_a  = sorted(set(a) - set(b))
    only_b  = sorted(set(b) - set(a))
    changed = sorted(k for k in (set(a) & set(b)) if a[k] != b[k])
    same    = len(set(a) & set(b)) - len(changed)

    print(f"\n  {args.a}  vs  {args.b}\n")

    if not only_a and not only_b and not changed:
        print(f"  {_c('identical', 'green')} ({same} shared key(s))\n")
        return

    for k in only_a:
        print(f"  {_c('─', 'red')} only in {args.a}: {k}")
    for k in only_b:
        print(f"  {_c('+', 'green')} only in {args.b}: {k}")
    for k in changed:
        if args.show_values:
            print(f"  {_c('~', 'yellow')} {k}:  {a[k]!r} → {b[k]!r}")
        else:
            print(f"  {_c('~', 'yellow')} changed: {k}")
    if same:
        print(f"\n  {same} key(s) unchanged")
    print()


def cmd_list(args):
    env = parse_env(args.env)
    if not env and not Path(args.env).exists():
        sys.exit(f"file not found: {args.env}")

    print(f"\n  {args.env}  ({len(env)} keys)\n")
    for k, v in sorted(env.items()):
        if args.show_values:
            print(f"  {k} = {v!r}")
        else:
            status = _c("set", "green") if v else _c("empty", "yellow")
            print(f"  {k}  [{status}]")
    print()


def cmd_lint(args):
    path = args.env
    if not Path(path).exists():
        sys.exit(f"file not found: {path}")

    lines = Path(path).read_text(encoding="utf-8").splitlines()
    issues: list[str] = []

    for lineno, raw in enumerate(lines, 1):
        stripped = raw.strip()

        if not stripped or stripped.startswith("#"):
            continue

        # leading/trailing whitespace on key
        if raw != raw.lstrip() and not raw.startswith(" "):
            pass  # tabs are probably fine

        bare = re.sub(r"^export\s+", "", stripped)

        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*", bare):
            issues.append(f"  line {lineno}: key doesn't start with a letter/underscore: {raw!r}")
            continue

        if "=" not in bare:
            issues.append(f"  line {lineno}: no '=' found (missing value?): {raw!r}")
            continue

        key_part = bare.split("=", 1)[0]
        if " " in key_part or "\t" in key_part:
            issues.append(f"  line {lineno}: space in key name: {raw!r}")

        val_part = bare.split("=", 1)[1]
        # mismatched quotes
        for q in ('"', "'"):
            if val_part.count(q) % 2 != 0:
                issues.append(f"  line {lineno}: unmatched {q} in value: {raw!r}")

    print(f"\n  lint: {path}\n")
    if issues:
        for msg in issues:
            print(_c(msg, "yellow"))
        print(f"\n  {_c(str(len(issues)) + ' issue(s)', 'red')}\n")
        sys.exit(1)
    else:
        print(f"  {_c('no issues found', 'green')}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        prog="envcheck",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version="1.1.0")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="command")

    sp = sub.add_parser("check",
                        help="check .env against a template")
    sp.add_argument("env",      nargs="?", default=".env")
    sp.add_argument("template", nargs="?", default=".env.example")
    sp.add_argument("--show-extra", action="store_true",
                    help="also report keys in .env but not in the template")

    sp = sub.add_parser("diff",
                        help="diff two .env files")
    sp.add_argument("a")
    sp.add_argument("b")
    sp.add_argument("--show-values", action="store_true",
                    help="print actual values (careful with secrets)")

    sp = sub.add_parser("list",
                        help="list all keys in a .env file")
    sp.add_argument("env", nargs="?", default=".env")
    sp.add_argument("--show-values", action="store_true")

    sp = sub.add_parser("lint",
                        help="check .env for formatting problems")
    sp.add_argument("env", nargs="?", default=".env")

    args = p.parse_args()
    {
        "check": cmd_check,
        "diff":  cmd_diff,
        "list":  cmd_list,
        "lint":  cmd_lint,
    }[args.cmd](args)


if __name__ == "__main__":
    main()

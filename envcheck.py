#!/usr/bin/env python3
"""envcheck: Validate .env files against a template. Zero dependencies."""

import sys
import os
import argparse
import re
from pathlib import Path


def parse_env(path: str) -> dict[str, str | None]:
    """Parse a .env file. Returns {key: value} (value is None if key has no value)."""
    result = {}
    try:
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)(?:=(.*))?$", line)
                if not m:
                    print(f"  [warn] {path}:{lineno}: cannot parse: {line!r}", file=sys.stderr)
                    continue
                key, val = m.group(1), m.group(2)
                if val is not None:
                    val = val.strip()
                    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                        val = val[1:-1]
                result[key] = val
    except FileNotFoundError:
        pass
    return result


RESET  = "\033[0m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"

def color(text, c):
    return f"{c}{text}{RESET}" if sys.stdout.isatty() else text


def cmd_check(args):
    env_file   = args.env
    tmpl_file  = args.template

    env  = parse_env(env_file)
    tmpl = parse_env(tmpl_file)

    missing     = [k for k in tmpl if k not in env]
    empty       = [k for k in tmpl if k in env and env[k] == ""]
    extra       = [k for k in env if k not in tmpl]
    ok          = [k for k in tmpl if k in env and env[k] != ""]

    print(f"\n  {color('envcheck', BOLD)}  {env_file}  vs  {tmpl_file}\n")
    print(f"  {color('✓', GREEN)} {len(ok)} keys present and set")

    if empty:
        print(f"  {color('!', YELLOW)} {len(empty)} keys present but empty:")
        for k in empty:
            print(f"      {color(k, YELLOW)}")

    if missing:
        print(f"  {color('✗', RED)} {len(missing)} keys missing from {env_file}:")
        for k in missing:
            example = tmpl.get(k)
            hint = f"  (example: {example!r})" if example else ""
            print(f"      {color(k, RED)}{hint}")

    if extra and args.show_extra:
        print(f"  {color('?', CYAN)} {len(extra)} extra keys not in template:")
        for k in extra:
            print(f"      {color(k, CYAN)}")

    print()
    if missing or empty:
        sys.exit(1)
    print(f"  {color('All required keys are set.', GREEN)}\n")


def cmd_diff(args):
    a = parse_env(args.a)
    b = parse_env(args.b)

    only_a = set(a) - set(b)
    only_b = set(b) - set(a)
    both   = set(a) & set(b)
    changed = {k for k in both if a[k] != b[k]}

    print(f"\n  Diff: {args.a}  vs  {args.b}\n")

    if only_a:
        print(f"  Only in {args.a}:")
        for k in sorted(only_a):
            print(f"    {color('- ' + k, RED)}")

    if only_b:
        print(f"  Only in {args.b}:")
        for k in sorted(only_b):
            print(f"    {color('+ ' + k, GREEN)}")

    if changed:
        print(f"  Value changed ({len(changed)} keys):")
        for k in sorted(changed):
            if not args.show_values:
                print(f"    {color('~ ' + k, YELLOW)}")
            else:
                print(f"    {color('~ ' + k, YELLOW)}:  {a[k]!r}  →  {b[k]!r}")

    if not only_a and not only_b and not changed:
        print(f"  {color('Files are identical.', GREEN)}")
    print()


def cmd_list(args):
    env = parse_env(args.env)
    print(f"\n  {args.env}  ({len(env)} keys)\n")
    for k, v in sorted(env.items()):
        if args.show_values:
            print(f"  {k} = {v!r}")
        else:
            status = color("set", GREEN) if v else color("empty", YELLOW)
            print(f"  {k}  [{status}]")
    print()


def cmd_lint(args):
    issues = 0
    try:
        with open(args.env, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        sys.exit(f"File not found: {args.env}")

    print(f"\n  Linting {args.env}\n")
    for lineno, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue
        if re.match(r"^\s+", line):
            print(f"  {color(f'line {lineno}', YELLOW)}: leading whitespace")
            issues += 1
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", stripped):
            print(f"  {color(f'line {lineno}', RED)}: invalid format: {line!r}")
            issues += 1
        elif "  " in stripped.split("=", 1)[0]:
            print(f"  {color(f'line {lineno}', YELLOW)}: spaces in key name")
            issues += 1

    if issues == 0:
        print(f"  {color('No issues found.', GREEN)}")
    else:
        print(f"\n  {color(str(issues) + ' issue(s) found.', RED)}")
        sys.exit(1)
    print()


def main():
    p = argparse.ArgumentParser(
        prog="envcheck",
        description="Validate .env files against a template. Zero dependencies.",
    )
    p.add_argument("--version", action="version", version="envcheck 1.0.0")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("check", help="Check .env against a template (.env.example)")
    sp.add_argument("env",      nargs="?", default=".env",         help=".env file")
    sp.add_argument("template", nargs="?", default=".env.example", help="Template file")
    sp.add_argument("--show-extra", action="store_true", help="Show keys not in template")

    sp = sub.add_parser("diff", help="Diff two .env files")
    sp.add_argument("a", help="First file")
    sp.add_argument("b", help="Second file")
    sp.add_argument("--show-values", action="store_true", help="Show actual values (careful with secrets!)")

    sp = sub.add_parser("list", help="List all keys in a .env file")
    sp.add_argument("env", nargs="?", default=".env")
    sp.add_argument("--show-values", action="store_true")

    sp = sub.add_parser("lint", help="Lint .env file for formatting issues")
    sp.add_argument("env", nargs="?", default=".env")

    args = p.parse_args()
    {"check": cmd_check, "diff": cmd_diff, "list": cmd_list, "lint": cmd_lint}[args.cmd](args)


if __name__ == "__main__":
    main()

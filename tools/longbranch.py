"""Turn branches that KickAssembler reports as out of range into long branches (jeq etc.,
src/macros.asm), then reassemble until none are left.

Usage: python tools/longbranch.py [-D SYMBOL ...]   (same defines as build.py)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(ROOT)]
import toolchain as tc  # noqa: E402

PATTERN = re.compile(r"jump distance is too far: -?\d+\)\.\s*\nat line (\d+), column \d+ in (\S+)")
BRANCH = re.compile(r"^(\s*(?:!\s*:\s*|[A-Za-z_]\w*:\s*)?)b(eq|ne|cc|cs|mi|pl)(\s)")


def assemble_errors(defines: list[str]) -> str:
    cmd = [tc.java(), "-jar", tc.kickass_jar(), tc.SRC / "main.asm", "-odir",
           (tc.BUILD / "longbranch").resolve(), "-libdir", (tc.BUILD / "generated").resolve(),
           "-libdir", tc.SRC.resolve()]
    for d in defines:
        cmd += ["-define", d]
    result = tc.run(cmd, capture_output=True, text=True)
    return result.stdout + result.stderr


def find_source(name: str) -> Path:
    path = Path(name)
    if path.is_absolute() and path.is_file():
        return path
    matches = list(tc.SRC.rglob(path.name)) + list((ROOT / "tests").rglob(path.name))
    if len(matches) != 1:
        raise SystemExit(f"cannot locate {name}: {matches}")
    return matches[0]


def main() -> None:
    defines = [a for i, a in enumerate(sys.argv[1:]) if sys.argv[i] == "-D"]
    for _ in range(200):
        out = assemble_errors(defines)
        m = PATTERN.search(out.replace("\r\n", "\n"))
        if not m:
            print("no out-of-range branches left")
            return
        line, source = int(m.group(1)), find_source(m.group(2))
        lines = source.read_text().split("\n")
        new = BRANCH.sub(lambda g: f"{g.group(1)}j{g.group(2)}{g.group(3)}", lines[line - 1], count=1)
        if new == lines[line - 1]:
            raise SystemExit(f"cannot fix {source}:{line}: {lines[line - 1]}")
        print(f"{source.relative_to(ROOT)}:{line}: {lines[line - 1].strip()} -> {new.strip()}")
        lines[line - 1] = new
        source.write_text("\n".join(lines))
    raise SystemExit("too many iterations")


if __name__ == "__main__":
    main()

import importlib
import sys
from pathlib import Path

from governance.rfa.declaration import digest_of
from scripts.rfa.gate import evaluate
from scripts.rfa.report import render


def main(name):
    module = importlib.import_module(f"governance.rfa.declarations.{name}")
    decl = module.DECLARATION
    verdict = evaluate(decl)
    out = Path("docs/reports") / f"{decl.name}_RFA.md"
    out.write_text(render(decl, verdict, digest_of(module.__file__)), encoding="utf-8")
    print(f"{decl.name}: {verdict.decision} (max power {verdict.max_power:.4f}) -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])

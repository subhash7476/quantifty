#!/usr/bin/env bash
# Run TLC on a spec/config pair, one invariant per run so each counterexample is short.
#   docs/tla/tlc.sh StaleLock StaleLock_Shipped.cfg
set -euo pipefail
cd "$(dirname "$0")"
SPEC="$1"; CFG="$2"
JAVA="${JAVA:-java}"
command -v "$JAVA" >/dev/null || JAVA="/c/Program Files/Java/jdk-27/bin/java"
[ -f tla2tools.jar ] || curl -sSL -o tla2tools.jar \
  https://github.com/tlaplus/tlaplus/releases/latest/download/tla2tools.jar
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
cp "$SPEC.tla" "$WORK/"
for inv in $(sed -n 's/^INVARIANTS //p' "$CFG"); do
  sed "s/^INVARIANTS.*/INVARIANTS $inv/" "$CFG" > "$WORK/run.cfg"
  echo "===== $CFG / $inv"
  (cd "$WORK" && "$JAVA" -XX:+UseParallelGC -cp "$OLDPWD/tla2tools.jar" tlc2.TLC \
     -deadlock -workers auto -metadir "$WORK/states_$inv" -config run.cfg "$SPEC.tla") \
    | grep -vE "^(Starting|Progress|Running|Parsing|Semantic|Computing|Implied|Finished|TLC2|The number|  because|Checking)" || true
done

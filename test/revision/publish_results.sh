#!/bin/bash
# Publish a campaign's analysed results through git, so they can be read off the server.
#
#   REV_DIR=runs/<name> bash test/revision/publish_results.sh
#
# Writes <REV_DIR>/analysis/ (relative to test/):
#   rev.csv                   analyze.py over <REV_DIR>/outs, one row per finished run
#   table_{STV,Q,steps}.csv   stv_table.py, a row per circuit and a column per configuration
#   table_{STV,Q,steps}.txt   the same tables as printed
#   status.txt                when, runs per configuration and status, Slurm jobs left
# then commits only that folder (test/runs/ is gitignored, hence add -f), pulls and pushes the
# current branch. Works on partial results: rerun it whenever there are new runs. Run it on the
# login node (seconds, standard library only).

set -euo pipefail
cd "$(dirname "$0")/.."  # -> test/
: "${REV_DIR:?set REV_DIR=runs/<name>, as for submit_revision.sh}"
[ -d "$REV_DIR/outs" ] || { echo "no $REV_DIR/outs here ($(pwd))" >&2; exit 1; }
type module &>/dev/null && module load python/3.12.10 || true  # as run_design.sh
[ -f ~/hbm/.venv/bin/activate ] && source ~/hbm/.venv/bin/activate || true

out="$REV_DIR/analysis"
mkdir -p "$out"
python3 ../scripts/revision/analyze.py "$REV_DIR/outs" --csv "$out/rev.csv"
for m in STV Q steps; do
    python3 ../scripts/revision/stv_table.py "$out/rev.csv" --metric "$m" \
        --csv "$out/table_$m.csv" > "$out/table_$m.txt"
done

{
    echo "updated $(date '+%F %T') on $(hostname -s), code at $(git rev-parse --short HEAD)"
    python3 - "$out/rev.csv" <<'EOF'
import csv, sys
from collections import Counter
rows = list(csv.DictReader(open(sys.argv[1])))
by = Counter((r["spec"], r["status"]) for r in rows)
print(f"{len(rows)} runs in rev.csv:", dict(Counter(r["status"] for r in rows)))
for spec in sorted({s for s, _ in by}):
    print(f"  {spec:13s}", "  ".join(f"{st} {n}" for (s, st), n in sorted(by.items()) if s == spec))
EOF
    if command -v squeue >/dev/null; then
        echo "Slurm: $(squeue -u "$USER" -h -r -t RUNNING | wc -l) tasks running," \
             "$(squeue -u "$USER" -h -r -t PENDING | wc -l) pending"
    fi
} > "$out/status.txt"
cat "$out/status.txt"

git add -f "$out"
if git diff --cached --quiet -- "$out/rev.csv"; then  # status.txt alone changes every time
    git reset -q -- "$out"
    git checkout -q -- "$out"
    echo "no new runs since the last publish: nothing committed"
else
    git commit -q -m "Results: $(basename "$REV_DIR") ($(($(wc -l < "$out/rev.csv") - 1)) runs)" -- "$out"
fi
branch=$(git rev-parse --abbrev-ref HEAD)
git pull -q --rebase --autostash origin "$branch"
git push -q origin "$branch"
echo "pushed $out to $branch"

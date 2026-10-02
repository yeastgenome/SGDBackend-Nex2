#!/bin/bash
# Pre-warm the backend's in-process GO enrichment cache by requesting
# regulation_target_enrichment for every locus that has regulation targets
# (see run_batter_enrichment in src/models.py; successful results are cached
# for BATTER_CACHE_TTL, default 24h). Run nightly, and after a backend
# restart — the cache is per-process, so restarting empties it.
#
# Requires NEX2_URI in the environment (source qa.sh / prod_variables.sh /
# prod.sh first) and a python with psycopg2 on PATH (source activate_env.sh;
# the prod boxes have no psql).
#
# Environment:
#   BACKEND_URLS  space-separated backend base URLs to warm, default
#                 $BACKEND_LOCAL_URL or http://127.0.0.1:6543. Point this at
#                 the public LB (https://backend.yeastgenome.org) when the
#                 nodes are not reachable directly.
#   PASSES        how many times to walk the regulator list, default 1. Use
#                 several passes through a load balancer so every node behind
#                 it gets each locus; repeat hits on an already-warm node are
#                 instant, so extra passes only cost the cold requests.
#
# Usage: prewarm_enrichment_cache.sh [max_loci]
#   max_loci: optional; warm only the first N regulators per pass (for testing)

set -u

BACKEND_URLS="${BACKEND_URLS:-${BACKEND_LOCAL_URL:-http://127.0.0.1:6543}}"
PASSES="${PASSES:-1}"
MAX_LOCI="${1:-0}"

if [ -z "${NEX2_URI:-}" ]; then
    echo "NEX2_URI is not set; source qa.sh, prod_variables.sh or prod.sh first" >&2
    exit 1
fi

PYTHON=$(command -v python || command -v python3)
if [ -z "$PYTHON" ]; then
    echo "no python on PATH; source activate_env.sh first" >&2
    exit 1
fi

# Warm the largest target lists first so the worst pages are covered even if
# the run is interrupted.
regulators=$("$PYTHON" - <<'PY'
import os
import psycopg2

conn = psycopg2.connect(os.environ['NEX2_URI'])
cur = conn.cursor()
cur.execute("""
    select d.format_name
      from nex.regulationannotation r
      join nex.dbentity d on d.dbentity_id = r.regulator_id
     group by d.format_name
     order by count(*) desc, d.format_name
""")
print("\n".join(row[0] for row in cur.fetchall()))
PY
)

if [ -z "$regulators" ]; then
    echo "no regulators found in nex.regulationannotation" >&2
    exit 1
fi
n_regulators=$(echo "$regulators" | wc -l | tr -d ' ')
echo "$(date '+%F %T') $n_regulators regulators; backends: $BACKEND_URLS; passes: $PASSES"

total=0
failed=0
start=$(date +%s)
pass=1
while [ "$pass" -le "$PASSES" ]; do
    for base in $BACKEND_URLS; do
        count=0
        for name in $regulators; do
            if [ "$MAX_LOCI" -gt 0 ] && [ "$count" -ge "$MAX_LOCI" ]; then
                break
            fi
            count=$((count + 1))
            total=$((total + 1))
            t0=$(date +%s)
            code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 600 \
                "$base/locus/$name/regulation_target_enrichment")
            elapsed=$(($(date +%s) - t0))
            if [ "$code" = "200" ]; then
                echo "$(date '+%F %T') pass $pass $base $name ok (${elapsed}s)"
            else
                failed=$((failed + 1))
                echo "$(date '+%F %T') pass $pass $base $name HTTP $code (${elapsed}s)"
            fi
        done
    done
    pass=$((pass + 1))
done
echo "$(date '+%F %T') done: $total requests, $failed failed, $(((
    $(date +%s) - start) / 60)) min total"
if [ "$failed" -gt 0 ]; then
    exit 1
fi

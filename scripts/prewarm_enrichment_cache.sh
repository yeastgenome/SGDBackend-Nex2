#!/bin/bash
# Pre-warm the backend's in-process GO enrichment cache by requesting
# regulation_target_enrichment for every locus that has regulation targets
# (see run_batter_enrichment in src/models.py; successful results are cached
# for BATTER_CACHE_TTL, default 24h). Run nightly, and after a backend
# restart — the cache is per-process, so restarting empties it.
#
# Requires NEX2_URI in the environment (source qa.sh / prod_variables.sh
# first) and a locally reachable backend (BACKEND_LOCAL_URL, default
# http://127.0.0.1:6543).
#
# Usage: prewarm_enrichment_cache.sh [max_loci]
#   max_loci: optional; warm only the first N regulators (for testing)

set -u

BACKEND_LOCAL_URL="${BACKEND_LOCAL_URL:-http://127.0.0.1:6543}"
MAX_LOCI="${1:-0}"

if [ -z "${NEX2_URI:-}" ]; then
    echo "NEX2_URI is not set; source qa.sh or prod_variables.sh first" >&2
    exit 1
fi

# Warm the largest target lists first so the worst pages are covered even if
# the run is interrupted.
regulators=$(psql "$NEX2_URI" -A -t -c \
    "select d.format_name
       from nex.regulationannotation r
       join nex.dbentity d on d.dbentity_id = r.regulator_id
      group by d.format_name
      order by count(*) desc, d.format_name")

if [ -z "$regulators" ]; then
    echo "no regulators found in nex.regulationannotation" >&2
    exit 1
fi

total=0
failed=0
start=$(date +%s)
for name in $regulators; do
    if [ "$MAX_LOCI" -gt 0 ] && [ "$total" -ge "$MAX_LOCI" ]; then
        break
    fi
    total=$((total + 1))
    t0=$(date +%s)
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 600 \
        "$BACKEND_LOCAL_URL/locus/$name/regulation_target_enrichment")
    elapsed=$(($(date +%s) - t0))
    if [ "$code" = "200" ]; then
        echo "$(date '+%F %T') $name ok (${elapsed}s)"
    else
        failed=$((failed + 1))
        echo "$(date '+%F %T') $name HTTP $code (${elapsed}s)"
    fi
done
echo "$(date '+%F %T') done: $total loci warmed, $failed failed, $(((
    $(date +%s) - start) / 60)) min total"
if [ "$failed" -gt 0 ]; then
    exit 1
fi

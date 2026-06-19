#!/usr/bin/env bash
#
# rebuild_qa.sh — pull latest main and rebuild SGDBackend-Nex2 on the QA box.
#
# Applies dependency changes that a plain service restart would NOT pick up:
#   - underscore bump (package.json / package-lock.json) -> needs a JS rebuild
#   - tornado removal  (requirements.txt)                -> install-time only
#
# Usage (run on the QA host, as the deploy user, from the app directory):
#   bash scripts/rebuild_qa.sh            # rebuild + verify (does NOT restart)
#   bash scripts/rebuild_qa.sh --restart  # also restart the service at the end
#
# The app directory defaults to APP_DIR below; override with:
#   APP_DIR=/path/to/app bash scripts/rebuild_qa.sh
#
set -euo pipefail

APP_DIR="${APP_DIR:-/data/www/SGDBackend-Nex2}"
VENV="${APP_DIR}/venv"
DO_RESTART=0
[[ "${1:-}" == "--restart" ]] && DO_RESTART=1

log()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m  ok: %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m  warn: %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m  ERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# --- 0. sanity ---------------------------------------------------------------
cd "$APP_DIR" 2>/dev/null || die "cannot cd to $APP_DIR"
[[ -f package.json && -f requirements.txt ]] || die "this does not look like the repo root"
command -v node >/dev/null || die "node not found on PATH"
command -v npm  >/dev/null || die "npm not found on PATH"
log "node $(node -v)   npm $(npm -v)"
# The legacy webpack-1 build pipeline needs an old Node; a very new Node will
# break `npm run build`. Warn (don't fail) so it's visible if the box drifted.
NODE_MAJOR="$(node -v | sed -E 's/^v([0-9]+).*/\1/')"
[[ "$NODE_MAJOR" -gt 12 ]] && warn "Node ${NODE_MAJOR} is newer than the legacy webpack-1 build expects; if 'npm run build' fails, use the Node version this app is pinned to."

PREV_HEAD="$(git rev-parse HEAD)"
log "current HEAD: ${PREV_HEAD:0:8}   (rollback: git reset --hard $PREV_HEAD)"

# --- 1. pull latest ----------------------------------------------------------
log "Pulling latest main"
git fetch origin main
git pull --ff-only origin main
ok "now at $(git rev-parse --short HEAD)"
echo "changed since previous HEAD:"
git --no-pager diff --stat "$PREV_HEAD" HEAD || true

# --- 2. activate venv --------------------------------------------------------
if [[ -f "${VENV}/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${VENV}/bin/activate"
  ok "venv active: $(python --version 2>&1)"
else
  warn "no venv at ${VENV} — using system python: $(python --version 2>&1)"
fi

# --- 3. frontend rebuild (applies the underscore fix) ------------------------
# npm ci installs EXACTLY the lockfile and fails if package.json/lock disagree,
# so it is the real test of the hand-edited lockfile entry. Fall back to
# `npm install` only if this npm is too old for `ci`.
log "Installing JS deps (npm ci)"
if npm ci; then
  ok "npm ci clean — lockfile and package.json agree"
else
  warn "npm ci failed (old npm or lock drift) — falling back to npm install"
  npm install
fi

# Confirm the resolved underscore version is the patched one.
US_VER="$(node -e "try{console.log(require('underscore/package.json').version)}catch(e){console.log('MISSING')}")"
[[ "$US_VER" == MISSING ]] && die "underscore not installed"
log "underscore resolved to ${US_VER}"
case "$US_VER" in
  1.1[2-9].*|1.[2-9][0-9].*) ok "patched (>= 1.12.1)";;
  *) die "expected >= 1.12.1, got ${US_VER} — lockfile not applied";;
esac

log "Building JS bundle (npm run build)"
# webpack 1 exits 0 even when individual modules fail to compile (e.g.
# unsupported JS syntax like optional chaining under Babel 6), so the exit
# code alone is not enough — scan the output for emitted errors too.
BUILD_LOG="$(mktemp)"
npm run build 2>&1 | tee "$BUILD_LOG"
if grep -qE 'ERROR in|Module build failed|Parsing error|SyntaxError' "$BUILD_LOG"; then
  rm -f "$BUILD_LOG"
  die "webpack reported module/parse errors — the bundle is BROKEN. Fix the source above and rebuild."
fi
rm -f "$BUILD_LOG"
if [[ -d src/build ]] && find src/build -type f -newermt "-10 minutes" | grep -q .; then
  ok "build clean — fresh artifacts present in src/build"
else
  warn "build reported no errors but no fresh files in src/build — check output above"
fi

# --- 4. python deps (applies the tornado change; no-op at runtime) -----------
log "Installing Python deps (pip install -r requirements.txt)"
pip install -r requirements.txt
# Install the local package editable via pip rather than `setup.py develop`.
# The legacy easy_install path used by `setup.py develop` fails to match
# twisted's normalized 'zope-interface' requirement against the installed
# 'zope.interface', and emits an UNKNOWN-0.0.0 egg. pip normalizes names
# correctly; --no-deps skips re-resolving the already-satisfied graph above.
log "Installing local package editable (pip install -e . --no-deps)"
pip install -e . --no-deps
ok "python deps installed"

# Confirm the app imports cleanly (covers the requirements.txt change).
log "Smoke-checking the app entry point"
if python -c "import src" 2>/dev/null; then
  ok "import src succeeded"
else
  warn "could not 'import src' directly — verify via the service start instead"
fi

# --- 5. restart --------------------------------------------------------------
if [[ "$DO_RESTART" == 1 ]]; then
  # On-box restart uses the Makefile pserve targets (the daemonized pid-file
  # pair). `make qa-restart` is Capistrano-from-a-workstation, not for here.
  log "Restarting the service (make stop-prod && make run-prod)"
  make stop-prod || warn "stop-prod returned non-zero (service may not have been running)"
  make run-prod
  ok "run-prod issued — confirm it came up (see verification below)"
else
  log "Skipping restart. To restart on the box:  make stop-prod && make run-prod"
fi

# --- 6. next steps -----------------------------------------------------------
cat <<'EOF'

================================================================================
 Rebuild complete. Manual verification:
   1. Service is up and serving (curl localhost / check logs for boot errors).
   2. Open a CURATION page in the browser and confirm it renders + works:
        - literature curation
        - file / spreadsheet upload
        - tagging
      These exercise the underscore code paths (findWhere/filter/clone/...).
   3. If anything is wrong, roll back:
        git reset --hard <PREV_HEAD printed above> && bash scripts/rebuild_qa.sh
================================================================================
EOF

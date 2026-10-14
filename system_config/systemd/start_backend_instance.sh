#!/bin/bash
# Entrypoint for sgd-backend@<port>.service: run another pserve process from
# the host's ini file, changing only the port.
#
#   start_backend_instance.sh <port>
#
# ENV_SCRIPT and INI_FILE come from /etc/default/sgd-backend-instance (the same
# env file and ini that the host's start.sh uses). The ini copy is regenerated
# on every start, so it never drifts from the main ini.
set -euo pipefail

PORT=${1:?usage: start_backend_instance.sh <port>}
REPO=/data/www/SGDBackend-Nex2
: "${ENV_SCRIPT:?ENV_SCRIPT not set (see /etc/default/sgd-backend-instance)}"
: "${INI_FILE:?INI_FILE not set (see /etc/default/sgd-backend-instance)}"

cd "$REPO"
# resolve the ini before sourcing the env script, which may set INI_FILE itself
SOURCE_INI=$(realpath "$INI_FILE")

# the env scripts echo their variables (incl. secrets); keep them out of logs
set +u
. "$(realpath "$ENV_SCRIPT")" > /dev/null 2>&1
set -u

# keep the copy next to the main ini so %(here)s resolves the same way
INSTANCE_INI="$(dirname "$SOURCE_INI")/.backend-$PORT.ini"
sed -E "/^\[server:main\]/,/^\[/ s/^port *=.*/port = $PORT/" "$SOURCE_INI" > "$INSTANCE_INI"
if ! grep -qE "^port = $PORT$" "$INSTANCE_INI"; then
    echo "could not set port $PORT in $INSTANCE_INI" >&2
    exit 1
fi

exec "$REPO/venv-py39/bin/pserve" "$INSTANCE_INI"

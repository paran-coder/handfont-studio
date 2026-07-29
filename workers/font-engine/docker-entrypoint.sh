#!/bin/sh
set -eu
if [ "${QUEUE_DRIVER:-vercel}" = "local" ]; then exec python -m worker.local_runner; fi
exec node queue-consumer.mjs

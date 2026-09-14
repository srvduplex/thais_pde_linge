#!/usr/bin/env bash
# Demande d'inventaire hebdomadaire (linge de lit), envoyee le jeudi avant la
# livraison du vendredi et le rush du week-end. Delai aleatoire (0-180 min)
# apres le declenchement cron pour ne pas arriver a heure fixe chaque semaine.
#
# Usage: run_inventory_request.sh [config.json] [fichier .env]
# Par defaut : Le Plat d'Etain / Elis.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

CONFIG_PATH="${1:-configs/plat_detain_elis.json}"
ENV_FILE="${2:-.env}"

DELAY_SECONDS=$(( RANDOM % 10800 ))
echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) : demande d'inventaire, delai aleatoire ${DELAY_SECONDS}s ==="
sleep "${DELAY_SECONDS}"

set -a
source "${ENV_FILE}"
set +a

python3 inventory_request.py --config "${CONFIG_PATH}"

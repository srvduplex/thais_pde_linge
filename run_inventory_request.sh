#!/usr/bin/env bash
# Demande d'inventaire (linge de lit), verifiee chaque jeudi mais envoyee
# seulement tous les ~21 jours (INTERVAL_DAYS) sauf si --force. Espacee
# davantage que chaque semaine sur demande de l'exploitant : si un controle
# revele un ecart trop important avec la realite, il suffit de relancer une
# demande ponctuelle plus tot via --force (cf. README/docs).
# Delai aleatoire (0-180 min) apres le declenchement cron pour ne pas arriver
# a heure fixe.
#
# Usage: run_inventory_request.sh [config.json] [fichier .env]
# Par defaut : Le Plat d'Etain / Elis.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

CONFIG_PATH="${1:-configs/plat_detain_elis.json}"
ENV_FILE="${2:-.env}"
SLUG="$(basename "${CONFIG_PATH}" .json)"
STATE_FILE="last_inventory_request_${SLUG}.txt"
CURSOR_FILE="inventory_cursor_${SLUG}.txt"
INTERVAL_DAYS="${INVENTORY_INTERVAL_DAYS:-21}"
GROUP_SIZE="${INVENTORY_GROUP_SIZE:-4}"

DELAY_SECONDS=$(( RANDOM % 10800 ))
echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) : verification demande d'inventaire (intervalle ${INTERVAL_DAYS}j), delai aleatoire ${DELAY_SECONDS}s ==="
sleep "${DELAY_SECONDS}"

set -a
source "${ENV_FILE}"
set +a

python3 inventory_request.py --config "${CONFIG_PATH}" --state-file "${STATE_FILE}" --interval-days "${INTERVAL_DAYS}" --cursor-file "${CURSOR_FILE}" --group-size "${GROUP_SIZE}"

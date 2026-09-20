#!/usr/bin/env bash
# Calcule et envoie la commande linge hebdomadaire (jour de livraison de la
# config -> 6 jours plus tard) pour un hotel donne. Lance par cron chaque lundi.
#
# Usage: run_weekly.sh [config.json] [fichier .env]
# Par defaut : Le Plat d'Etain / Elis (pour compatibilite avec le cron existant).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

CONFIG_PATH="${1:-configs/plat_detain_elis.json}"
ENV_FILE="${2:-.env}"
SLUG="$(basename "${CONFIG_PATH}" .json)"
CARRYOVER_FILE="carryover_${SLUG}.json"

set -a
source "${ENV_FILE}"
set +a

read -r DATE_FROM DATE_TO <<< "$(python3 -c "
import datetime
import config as cfg
hc = cfg.load_config('${CONFIG_PATH}')
today = datetime.date.today()
date_from = today + datetime.timedelta(days=(hc.delivery_weekday - today.weekday()) % 7)
date_to = date_from + datetime.timedelta(days=6)
print(date_from.isoformat(), date_to.isoformat())
")"

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) : [${SLUG}] commande linge pour la semaine ${DATE_FROM} -> ${DATE_TO} ==="

python3 linge_commande.py \
  --config "${CONFIG_PATH}" \
  --from-date "${DATE_FROM}" \
  --to-date "${DATE_TO}" \
  --notify-smtp \
  --out-html "commande_${SLUG}_${DATE_FROM}.html" \
  --snapshot-json "commande_${SLUG}_${DATE_FROM}.json" \
  --carryover-file "${CARRYOVER_FILE}"

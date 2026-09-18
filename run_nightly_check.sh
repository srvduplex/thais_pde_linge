#!/usr/bin/env bash
# Verification nocturne (22h, fermeture des checkin) pour un hotel donne :
# compare le besoin en linge recalcule a la commande du lundi (snapshot) pour
# la fenetre de stock en cours, et alerte si des chambres ajoutees depuis
# entament le stock de securite (20% de la quantite commandee par reference).
#
# Usage: run_nightly_check.sh [config.json] [fichier .env]
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

ACTIVE_FRIDAY="$(python3 -c "
import datetime
today = datetime.date.today()
days_since_friday = (today.weekday() - 4) % 7
print((today - datetime.timedelta(days=days_since_friday)).isoformat())
")"

SNAPSHOT="commande_${SLUG}_${ACTIVE_FRIDAY}.json"

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) : [${SLUG}] verification stock, fenetre debutant ${ACTIVE_FRIDAY} ==="

if [[ ! -f "${SNAPSHOT}" ]]; then
  echo "Snapshot ${SNAPSHOT} introuvable (pas de commande enregistree pour cette fenetre) — verification ignoree."
  exit 0
fi

python3 verif_stock.py --config "${CONFIG_PATH}" --snapshot-json "${SNAPSHOT}" --carryover-file "${CARRYOVER_FILE}" --notify-smtp

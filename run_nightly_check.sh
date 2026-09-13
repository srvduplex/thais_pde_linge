#!/usr/bin/env bash
# Verification nocturne (22h, fermeture des checkin) : compare le besoin en
# linge recalcule a la commande Elis du lundi (snapshot) pour la fenetre de
# stock en cours, et alerte si des chambres ajoutees depuis entament le stock
# de securite (20% de la quantite commandee par reference).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

set -a
source .env
set +a

ACTIVE_FRIDAY="$(python3 -c "
import datetime
today = datetime.date.today()
days_since_friday = (today.weekday() - 4) % 7
print((today - datetime.timedelta(days=days_since_friday)).isoformat())
")"

SNAPSHOT="commande_${ACTIVE_FRIDAY}.json"

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) : verification stock, fenetre debutant ${ACTIVE_FRIDAY} ==="

if [[ ! -f "${SNAPSHOT}" ]]; then
  echo "Snapshot ${SNAPSHOT} introuvable (pas de commande enregistree pour cette fenetre) — verification ignoree."
  exit 0
fi

python3 verif_stock.py --snapshot-json "${SNAPSHOT}" --notify-smtp

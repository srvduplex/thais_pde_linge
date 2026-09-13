#!/usr/bin/env bash
# Calcule et envoie la commande linge Elis hebdomadaire (vendredi -> jeudi suivant).
# Lance par cron chaque lundi. Voir README.md pour le detail.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

set -a
source .env
set +a

read -r DATE_FROM DATE_TO <<< "$(python3 -c "
import datetime
today = datetime.date.today()
date_from = today + datetime.timedelta(days=(4 - today.weekday()) % 7)
date_to = date_from + datetime.timedelta(days=6)
print(date_from.isoformat(), date_to.isoformat())
")"

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) : commande linge pour la semaine ${DATE_FROM} -> ${DATE_TO} ==="

python3 linge_commande.py \
  --from-date "${DATE_FROM}" \
  --to-date "${DATE_TO}" \
  --notify-smtp \
  --out-html "commande_${DATE_FROM}.html"

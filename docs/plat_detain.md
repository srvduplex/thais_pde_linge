# Le Plat d'Étain / Elis — méthode de calcul et décisions

Document de suivi (comme `docs/bois_guibert.md`) : la méthode de calcul de la
commande linge et les décisions prises au fil des échanges.

## Méthode de calcul (état au 2026-10-05)

1. **Fenêtre** : cron le lundi 7h → nuits du vendredi de livraison au jeudi suivant (7 nuits).
2. **Réservations** : API Thaïs (`/hotel/bookings`), hors annulations et no-shows.
   Le jour de séjour réel compte (jour 1 = arrivée), même si l'arrivée précède la fenêtre.
3. **Linge de lit** : mise à blanc les jours 1, 5, 9… — dotation par catégorie
   (double / twin / triple) + 2 taies 65x65 + 2 taies 50x80 fixes.
4. **Linge de bain** (drap de bain, serviette, tapis) — `bath_stayover_rate: 0.3` :
   - jour d'arrivée et jours de mise à blanc : 100 % ;
   - toutes les autres nuits : **30 %** (part estimée des clients en recouche qui demandent un change) ;
   - drap de bain et serviette = nb d'occupants (adultes + enfants), tapis = 1 (double) ou 2 (twin, triple) ;
   - total arrondi au-dessus par référence, une seule fois sur la semaine.
5. **Ajustements**, dans l'ordre : report de l'écart de la semaine précédente
   (contrôle de 22h), stock compté si fourni ponctuellement (`--stock`), minimum Elis de 20.
6. **Envoi** direct à Elis, numéro `semaine/PDE`, garde-fou anti-doublon (`order_log_plat_detain_elis.jsonl`).

## Décisions

- **2026-10-05 — Recouche bain à 70 % (option B).** Avant : linge de bain changé
  tous les 2 jours (jours 1, 3, 5…), rien les jours pairs. Mathieu a choisi de
  remplacer ce cycle par 100 % à l'arrivée puis 70 % chaque nuit suivante.
  Le taux de 70 % est une estimation, à affiner avec les données du module de
  comptage Thaïs (ci-dessous). Effet sur la semaine du 9 au 15/10 :
  drap de bain et serviette 18 → 25, tapis 15 → 20.
  La commande 41/PDE (9→15/10) était déjà partie avec l'ancienne règle :
  l'écart sera repris par le report dans la commande du 12/10.
  Bois Guibert reste sur le cycle 2 jours (option absente de sa config) tant
  que ce n'est pas décidé.

- **2026-10-05 (plus tard) — taux ramené de 70 % à 30 %.** Les comptages Thaïs
  de Bois Guibert montrent 15-23 % de change bain en recouche ; Mathieu retient
  30 % pour le Plat d'Étain en attendant ses propres comptages.

## Module de comptage de linge Thaïs

- Accessible en lecture par l'API : `GET /hub/api/partner/hotel/room-states?date=YYYY-MM-DD`,
  champ `nb_linens` = `{id_type_linge: quantité}` par chambre (12 types : 2, 5, 8 … 35).
- L'API ne fournit pas le nom des types : la correspondance avec les références
  Elis est à relever dans l'écran Thaïs (ex. 8 = drap de bain ?).
- Pour une date, l'API renvoie le dernier état saisi de chaque chambre, pas un
  historique jour par jour : il faut une saisie à chaque chambre faite.
- Au 2026-10-05, quasiment inutilisé (une seule saisie test, chambre 11 Halles, 8-9/09).
- **Prochaine étape** : Mathieu forme la femme de chambre au module (octobre 2026).
  Après quelques semaines de saisies : relever la correspondance types ↔ références,
  mesurer le vrai taux de change en recouche et remplacer les 70 % estimés.

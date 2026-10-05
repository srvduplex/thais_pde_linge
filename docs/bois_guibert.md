# Bois Guibert / Anett — notes de mise en place

Second hôtel sur ce même projet (moteur partagé avec Le Plat d'Étain / Elis,
voir `config.py` et `configs/`). Ce document trace les décisions et l'état
d'avancement au fil des échanges, pour ne rien reperdre entre deux sessions.

## Établissement

- Nom Thaïs : **Hôtel du Château Bois-Guibert** (Bonneval, RN 10, 28800)
- URL Thaïs : `https://boisguibert.thais-hotel.com`
- Identifiants API : `.env.boisguibert` (`THAIS_USERNAME=api_cbg`), permissions 600, jamais commité
- Fournisseur linge : **Anett** (Anett Centre Loire, agence La Chaussée-St-Victor)
  compte client `S379900`, contact facturation `anett.centreloire@anett.fr`
- Contact interne pour la commande hebdo (recap SMTP, puisque la commande doit
  être saisie manuellement par Gwennaëlle sur le site Anett, pas de brouillon
  direct fournisseur) : `contact@bois-guibert.com`
- **Cycle commande/livraison : commande le LUNDI, livraison le JEUDI**
  (différent du Plat d'Étain qui livre le vendredi) — confirmé par Mathieu le
  20/09/2026. La fenêtre hebdo calculée est donc jeudi→mercredi (7 nuits),
  pas vendredi→jeudi.
- Règles métier communes avec Plat d'Étain : cycle 2/4 jours, mise à blanc,
  4 oreillers fixes par changement complet.
- Minimum de commande : **10** par référence (vs 20 pour Elis/Plat d'Étain).
- Lit d'appoint : seuil **>3 occupants**, taille **90×190**, dotation = drap
  0040BF + housse 1532AN (mêmes références que le Twin, cohérent avec le fait
  que c'est un lit simple de plus dans la chambre).
- Stock de sécurité par pourcentage : **pas encore défini** (pas d'inventaire
  fait à ce jour, cf. points ouverts).

## Catégories de chambres Thaïs (22 chambres réelles, hors "Hors chambre"/"FICTIVE")

| room_type_id | Libellé Thaïs | Capacité max | Chambres |
|---|---|---|---|
| 1 | Chambre Twin Supérieure - Château | 2 | 1, 9 |
| 2 | Chambre Double Supérieure - Château | 2 | 5, 6, 11, 12, 14, 15 |
| 3 | Chambre Double Standard - Château | 2 | 3, 10 |
| 4 | Chambre Triple Supérieure - Château | 3 | 2, 4, 8 |
| 5 | Chambre Double Deluxe - Douves | 3 | 17, 18, 19, 20 |
| 8 | Chambre Twin Deluxe - Douves | 3 | 16, 21 |

La distinction Château/Douves n'a **aucun impact** sur le linge, et 140 vs 160
utilisent finalement la **même dotation** (voir référentiel ci-dessous) — donc
**aucun `room_label_to_categorie` n'est nécessaire**, `label_to_categorie`
suffit pour les 6 catégories Thaïs.

La Chambre 8 était mal classée "Double Supérieure - Château" ; Mathieu l'a
corrigée dans Thaïs directement (confirmé par extraction API le 13/09/2026),
elle est maintenant "Triple Supérieure - Château".

## Référentiel Anett et dotation (CONFIRMÉ, dans `configs/bois_guibert_anett.json`)

Sources croisées : 2 factures réelles (`doc/*.pdf`) + liste complète de
Gwennaëlle (`doc/Liste_references_articles_Anett.docx`, 14/09/2026).

| Code | Désignation | Dimension | Liseret | Section |
|---|---|---|---|---|
| 0040BF | Drap blanc Open End | 180×320 | — | lit |
| 0050BE | Drap blanc | 240×320 | — | lit |
| 0510BV | Taie blanche (carrée) | 68×68 | — | lit |
| 0511BS | Taie sac américaine (rectangulaire) | 55×90 | — | lit |
| 1532AN | Housse de couette Simply | 160×260 | Orange | lit |
| 1533AN1 | Housse de couette Simply | 265×280 | Noir | lit |
| 0300BE | Drap de bain grec | 70×140 | — | bain |
| 0320BE | Serviette grec | 50×90 | — | bain |
| 0310BE | Tapis de bain | 50×75 | — | bain |
| 0130BF | Nappe Luna (restaurant) | 160×160 | — | restaurant |

(Exclus : sacs polyester 2100GA/JA/OA, DA005A, 1320C3 (contestée), frais
administratifs — pas du linge.)

**Dotation par catégorie (confirmée le 20/09/2026)** :
- **Double (140 et 160 identiques)** : 1× drap 0040BF + 1× housse 1533AN1 (noir)
- **Twin (par lit, 2 lits séparés)** : 2× drap 0040BF + 2× housse 1532AN (orange)
- **Triple (160+90 combiné)** : 1× drap 0050BE (un seul grand drap couvrant les
  deux matelas) + 1× housse 1533AN1 (noir, côté 160) + 1× housse 1532AN
  (orange, côté 90)
- **Taies fixes** (tout changement complet, toute catégorie) : 2× 0510BV + 2× 0511BS
- **Tapis de bain** : double=1, twin=2, triple=2 (par nombre de lits, comme au Plat d'Étain)
- **Drap de bain/serviette** : par occupant, cycle 2 jours (identique Plat d'Étain)
- **Lit d'appoint** (>3 occupants) : + 1× drap 0040BF + 1× housse 1532AN

## Bug corrigé le 20/09/2026

Le moteur (`compute_needs_from_bookings`) avait les codes de linge de bain
Elis ("8786"/"8785"/"8787") codés en dur au lieu d'utiliser la config —
plantait au premier calcul Bois Guibert (KeyError). Corrigé en ajoutant
`drap_bain_code`/`serviette_code`/`tapis_bain_code` à `HotelConfig`
(obligatoires, sans défaut Elis implicite). Voir commit `d18380f`.

## Première commande (20/09/2026)

Calculée pour la fenêtre 24/09→30/09 (premier cycle jeudi-mercredi) et
envoyée par email à `contact@bois-guibert.com` (pas de stock déduit, pas de
minimum appliqué visible car tout était déjà au-dessus de 10) :
0040BF=28, 0050BE=10, 0510BV=62, 0511BS=62, 1532AN=15, 1533AN1=27, 0300BE=58,
0320BE=58, 0310BE=42.

**Mise en garde envoyée à Gwennaëlle** : cette première commande ne tient pas
compte du stock existant (pas d'inventaire encore fait) — elle doit
vérifier/réduire certaines références avant de saisir sur le site Anett.

## Demande d'inventaire (mise en place le 20/09/2026)

Même mécanisme que Plat d'Étain : `run_inventory_request.sh
configs/bois_guibert_anett.json .env.boisguibert`, cron jeudi 7h UTC + délai
aléatoire 0-180min, rotation par groupes de 4 références (sur les 9
références lit+bain), envoyée à `contact@bois-guibert.com`. Pas encore de
premier inventaire réel reçu — état/curseur (`last_inventory_request_bois_guibert_anett.txt`,
`inventory_cursor_bois_guibert_anett.txt`) reste à zéro jusqu'au premier envoi.

## Points ouverts

1. **Pas d'inventaire de stock encore fait** — donc pas de fichier
   `stock_bois_guibert_anett.csv`, toutes les commandes jusqu'ici sont sur le
   besoin brut (sans déduction de stock). Un inventaire sur 4-5 références est
   prévu cette semaine (voir demande d'inventaire ci-dessus).
2. **Carryover pas encore actif** : le principe (voir mémoire projet
   `feedback`/`project` — commande verrouillée jusqu'au lundi suivant, donc
   les écarts doivent être absorbés dans la commande suivante) s'applique
   aussi à Bois Guibert par confirmation de Mathieu (20/09/2026), mais
   `run_weekly.sh`/`run_nightly_check.sh` ne sont pas encore en cron pour cet
   hôtel — seule la demande d'inventaire l'est pour l'instant.
3. **% de stock de sécurité** pour `verif_stock.py --safety-stock-pct` : pas
   défini pour Bois Guibert (20% est la valeur Plat d'Étain, pas confirmée ici).

## Prochaines étapes

1. Récupérer la réponse de Gwennaëlle sur la première commande (ajustements de stock).
2. Premier inventaire réel (4-5 références, via la demande automatique du jeudi).
3. Une fois un stock de référence connu, ajouter `run_weekly.sh` et
   `run_nightly_check.sh` au cron pour Bois Guibert (avec `--carryover-file`
   comme au Plat d'Étain), sur le cycle lundi/jeudi.

## Module de comptage de linge Thaïs (analyse du 2026-10-05)

Les femmes de chambre de Bois Guibert utilisent le module : 564 comptages sur
le 07/08 → 04/10, lus en lecture seule via
`GET /hub/api/partner/hotel/room-states?date=…` (champ `nb_linens`), puis croisés
avec les réservations (`/hotel/bookings`, jointure sur le libellé de chambre).

**Correspondance des numéros de type, déduite des données (À FAIRE CONFIRMER
dans l'écran Thaïs)** :

| Type Thaïs | Valeur typique | Hypothèse |
|---|---|---|
| 5 | 1 | grand drap (lit double) |
| 23 | 1 | grande housse de couette |
| 2 | 1-2 | petit drap (lit 90 : twin séparé, 3e lit) |
| 20 | 1-2 | petite housse (lit 90) |
| 8 | 2-3 | taie (type 1) |
| 24 | 2-3 | taie (type 2) |
| 11 | 2-3 | drap de bain |
| 14 | 2-3 | serviette |
| 17 | 1 | tapis de bain |

**Constats** (écarts avec `configs/bois_guibert_anett.json`, rien n'est modifié) :

1. **Recouche bain ≈ 15-23 %, loin des 70 % estimés au Plat d'Étain.** Sur 151
   nuits de recouche : 101 comptages, dont 23 avec change bain (23 %) ; si les
   50 recouches sans comptage = aucun change, 23/151 = 15 %. Linge de lit en
   recouche : 6 cas seulement.
2. **Tapis : 1 par chambre** quelle que soit la catégorie (la config compte 2
   en twin et triple).
3. **Bain dressé pour 2 même avec 1 occupant** : sur 87 départs avec 1 occupant
   réservé, 2 draps de bain et 2 serviettes comptés (le calcul en compte 1).
   **Décision Mathieu (2026-10-05)** : c'est la pratique qui doit changer, pas
   le calcul — CBG ne doit dresser le bain que pour 1 personne quand il y a un
   seul occupant. Calcul inchangé (1 par occupant). À revérifier dans les
   comptages Thaïs dans quelques semaines.
4. **Twin le plus souvent fait en lit double** : 51 départs twin en grand drap +
   grande housse contre ~19 en 2 petits lits.
5. Couverture : 310 départs comptés sur 423 (73 %). 77 comptages tombent le jour
   d'arrivée sans départ la veille (chambre préparée avant l'arrivée).

**2026-10-05 — synthèse de la méthode envoyée à Gwennaëlle** (contact@bois-guibert.com,
cc Mathieu) : méthode de calcul, constats des comptages Thaïs, consigne « 1 seul
occupant = bain pour 1 personne », encouragement à continuer la saisie Thaïs.

**2026-10-05 — corrections appliquées à la config** (décision Mathieu, suite à
l'analyse des comptages) : `bath_stayover_rate: 0.2` (bain 100 % à l'arrivée et
aux mises à blanc, 20 % les autres nuits, au lieu du cycle 2 jours) et
`tapis_par_categorie` = 1 tapis par chambre dans toutes les catégories (au lieu
de 2 en twin/triple). Effet dès la commande du 12/10 (semaine 15→21/10).

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
- Contact pour la commande hebdo (recap SMTP, puisque la commande doit être
  saisie manuellement sur le site Anett, pas de brouillon direct) : `contact@bois-guibert.com`
- Règles métier : **identiques** à Plat d'Étain (cycle 2/4 jours, mise à
  blanc, 4 oreillers fixes par changement complet, commande lundi/livraison
  vendredi, 20% stock de sécurité provisoire)

## Catégories de chambres Thaïs (22 chambres réelles, hors "Hors chambre"/"FICTIVE")

| room_type_id | Libellé Thaïs | Capacité max | Chambres |
|---|---|---|---|
| 1 | Chambre Twin Supérieure - Château | 2 | 1, 9 |
| 2 | Chambre Double Supérieure - Château | 2 | 5, 6, 11, 12, 14, 15 (8 déplacée en Triple, voir plus bas) |
| 3 | Chambre Double Standard - Château | 2 | 3, 10 |
| 4 | Chambre Triple Supérieure - Château | 3 | 2, 4, **8** |
| 5 | Chambre Double Deluxe - Douves | 3 | 17, 18, 19, 20 |
| 8 | Chambre Twin Deluxe - Douves | 3 | 16, 21 |

La distinction Château/Douves n'a **aucun impact** sur le linge — seul le
type/taille de lit compte.

### Correction Thaïs

La Chambre 8 était classée "Double Supérieure - Château" mais est en réalité
une Triple (160+90) — Mathieu a corrigé le room_type directement dans Thaïs
(confirmé par extraction API le 13/09/2026). Elle se comporte donc
normalement via `label_to_categorie`, sans besoin d'override
`room_label_to_categorie`.

### Mapping lit par numéro de chambre (car une même catégorie Thaïs mélange 140 et 160)

| Chambre | Taille de lit |
|---|---|
| 5, 11, 14, 15 | 140 |
| 12, 6 | 160 |
| 3, 10 | 140 |
| 2, 4, 8 | Triple (160 + 90) |
| 1, 9 | Twin (2× 90) |
| 16, 21 | Twin Deluxe (2× 90) |
| 17, 18, 19, 20 | 160 (Double Deluxe) |

→ nécessitera un `room_label_to_categorie` dans `configs/bois_guibert_anett.json`
pour les chambres 5,6,11,12,14,15,3,10 (mélange 140/160 au sein d'une même
catégorie Thaïs) ; les autres catégories peuvent rester sur `label_to_categorie`.

## Référentiel Anett

Deux sources croisées : 2 factures réelles (`doc/*.pdf`, 24/11/24-28/12/24 et
29/12/24-25/01/25, codes identiques sur les deux) + la liste compilée par
Gwennaëlle le 14/09/2026 (`doc/Liste_references_articles_Anett.docx`, à partir
des bons de livraison et de la facture de juillet).

| Code | Désignation (Gwennaëlle) | Dimension | Liseret |
|---|---|---|---|
| 0040BF | Drap blanc Open End | 180×320 | — |
| 0050BE | Drap blanc | 240×320 | — |
| 0300BE | Drap de bain grec blanc | 70×140 | — |
| 0310BE | Tapis de bain blanc | 50×75 | — |
| 0320BE | Serviette grec blanc | 50×90 | — |
| 0510BV | Taie blanche (carrée) | 68×68 | — |
| 0511BS | Taie sac américaine blanche (rectangulaire) | 55×90 | — |
| 1532AN | Housse de couette Simply blanc | 160×260 | Orange |
| 1533AN1 | Housse de couette Simply blanc | 265×280 | Noir |
| 0130BF | Nappe Luna blanc (restaurant) | 160×160 | — |

(Exclus : sacs polyester logistique 2100GA/JA/OA, DA005A (housse cabriolet
fauteuil), 1320C3 (porte-sacs, référence contestée par Gwennaëlle, absente
des bons de juillet), frais administratifs PPE/PCE/contribution
énergie/abonnement/TBV — pas du linge.)

**0511BS (taie rectangulaire) trouvée le 14/09** — absente des 2 factures
consultées mais présente dans la liste de Gwennaëlle. Résout le point ouvert
sur la 2e taie : 4 oreillers = 2× 0510BV (carrée) + 2× 0511BS (rectangulaire),
cohérent avec le Plat d'Étain.

## Points ouverts (à ne pas deviner)

1. **Mapping drap/housse ↔ taille de lit** : hypothèse de travail (à confirmer
   par Mathieu avec les codes exacts) —
   - drap 0040BF (180×320) + housse 1532AN (160×260, orange) = jeu "double" (140 et/ou 160 ?)
   - drap 0050BE (240×320) + housse 1533AN1 (265×280, noir) = jeu "combo" pour
     le lit combiné des Triple (160+90 ensemble), par analogie avec le
     "265 bleu marine" d'Elis au Plat d'Étain
   - Reste à savoir comment les chambres Twin (2 lits 90 séparés) sont couvertes
     (même jeu que le double, par lit ? autre chose ?)
2. **Lit d'appoint (>3 occupants → 90×190)** : le moteur supporte déjà
   `extra_bed_threshold`/`extra_bed_dotation` (voir `config.py`), mais les codes
   Anett exacts pour ce lit d'appoint restent à préciser.

## Prochaines étapes

1. Résoudre les points ouverts ci-dessus avec Mathieu.
2. Construire `configs/bois_guibert_anett.json` (référentiel + dotation +
   room_label_to_categorie + coordonnées Anett/contact@bois-guibert.com).
3. Créer `.env.boisguibert` avec THAIS_USERNAME/PASSWORD (fait) + SMTP_TO=contact@bois-guibert.com.
4. Ajouter les entrées crontab pour Bois Guibert (`run_weekly.sh configs/bois_guibert_anett.json .env.boisguibert`
   et `run_nightly_check.sh` idem), en s'assurant qu'elles ne rentrent pas en
   collision avec celles du Plat d'Étain (même VPS, fichiers de snapshot déjà
   préfixés par le slug de config depuis le refactoring multi-hôtel).

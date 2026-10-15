# Textes juridiques de Boufbowl

Les six textes en français sont des projets propres aux fonctionnalités du dépôt.
Les informations et décisions non connues sont représentées par `[]`, sans identité,
adresse, autorisation de propriété intellectuelle ou durée de conservation inventée.

- [Politique de confidentialité](confidentialite.md)
- [Conditions générales d’utilisation](conditions-utilisation.md)
- [Mentions légales](mentions-legales.md)
- [Cookies, traceurs et stockage local](cookies.md)
- [Charte communautaire](charte-communaute.md)
- [Règlement général des tournois](reglement-tournois.md)

## Modifier et consulter les textes

Modifier les fichiers Markdown, puis régénérer les sept pages publiques :

```sh
python3 -m tools.build_legal_pages
python3 -m tools.build_legal_pages --check
```

L’index est `/legal.html`. Chaque texte possède sa propre page HTML à la racine
avec le même nom que sa source Markdown. Les pages sont lisibles sans JavaScript,
imprimables et liées depuis le jeu.
Le statut de projet et les champs `[]` restent visibles ; les pages portent une
directive `noindex` tant qu’elles sont livrées comme projets.

## Informations à renseigner par l’exploitant

- Identité, statut, coordonnées, directeur de publication, immatriculation et TVA
  lorsque ces indications sont applicables.
- Entité Oracle contractante, fournisseurs de réseau et de sauvegarde, localisation des sauvegardes, transferts et garanties.
- Bases légales par finalité, intérêts légitimes éventuels et durées de conservation.
- Âge minimal, gestion des mineurs, contacts pour les droits et les réclamations.
- Titulaires de droits sur le jeu, crédits, affiliations et autorisations réelles.
- Présentation et acceptation des CGU, gestion des changements, support et recours.
- Conditions propres aux éditions des tournois et aux éventuels lots externes.

## Points de fonctionnement à aligner avec les textes finalisés

Les documents décrivent le code actuel ; ils n’ajoutent pas de mécanismes de
consentement, d’effacement, d’export des données ou de purge. La conservation
actuelle des principales tables ne comporte pas de politique générale de purge.
Les durées choisies doivent donc être accompagnées des procédures correspondantes.
La période affichée dans un tableau de statistiques n’est pas une durée d’effacement.

La télémétrie utilise un identifiant local et des données liées au profil. Son
exemption de consentement n’est pas établie par la simple rédaction de la notice.
L’exploitant doit déterminer le régime applicable et, si nécessaire, mettre en
place le contrôle préalable et le retrait du consentement. Le projet n’affiche
pas de bouton fictif prétendant désactiver une collecte qu’il ne contrôle pas.

La fermeture d’un compte et l’exercice des droits sont actuellement à organiser
par contact ; aucun portail de suppression automatique n’est annoncé. La mise à
disposition des CGU n’ajoute pas de preuve d’acceptation à l’inscription. Les textes
n’accordent aucune autorisation sur des éléments de jeu appartenant à des tiers.
Le règlement général ne crée pas de mécanisme automatique de disqualification,
de remise de lots externes ou de traitement de réclamations qui serait absent du jeu.

## Références vérifiées pour la rédaction

Les références suivantes apportent un cadre d’information ; elles ne déterminent
pas à elles seules le statut, les obligations territoriales ou les choix de
l’exploitant, laissés à compléter dans les textes.

- [CNIL — Information des personnes et transparence](https://www.cnil.fr/fr/conformite-rgpd-information-des-personnes-et-transparence) : identité, finalités, bases légales, destinataires, durées, transferts et droits.
- [CNIL — Exemples de mentions d’information](https://www.cnil.fr/fr/passer-laction/rgpd-exemples-de-mentions-dinformation) : présentation accessible des informations.
- [CNIL — Droits sur les données](https://www.cnil.fr/fr/passer-laction/les-droits-des-personnes-sur-leurs-donnees) : droits à distinguer selon leur applicabilité.
- [CNIL — Répondre à une demande d’accès](https://cnil.fr/fr/repondre-une-demande-de-droit-dacces) : délai de réponse et vérification proportionnée de l’identité.
- [CNIL — Droit à l’effacement](https://www.cnil.fr/fr/comprendre-mes-droits/le-droit-leffacement-supprimer-vos-donnees-en-ligne) : limites et prolongation du délai dans les conditions légales.
- [CNIL — Règles relatives aux cookies](https://www.cnil.fr/fr/cookies-et-autres-traceurs/regles/cookies) : information, consentement et exemptions.
- [CNIL — Questions-réponses sur les traceurs](https://www.cnil.fr/fr/cookies-et-autres-traceurs/regles/cookies/FAQ) : distinction entre authentification, sécurité et autres finalités.
- [Service Public — Mentions obligatoires pour un entrepreneur individuel](https://entreprendre.service-public.gouv.fr/vosdroits/F31228) : indications à adapter au statut de l’éditeur.

L’hébergement Oracle à Paris est renseigné d’après les indications de l’exploitant.
Les coordonnées publiques d’Oracle France proviennent de sa
[page de contact officielle](https://www.oracle.com/fr/corporate/contact/).
La région Paris (eu-paris-1) figure dans la
[documentation Oracle des régions](https://docs.oracle.com/fr-fr/iaas/database-migration/doc/region-availability.html).
L’adresse de contact d’Oracle France n’est pas présentée comme l’adresse physique
du centre de données ni comme la preuve de l’identité de l’entité contractante.

Les descriptions techniques s’appuient notamment sur `backend/storage.py`,
`backend/accounts.py`, `backend/tracking.py`, `backend/moderation.py`,
`backend/admin.py`, `backend/tournaments.py`, `backend/tournament_rounds.py`,
`patches/ServerSupport.as.inc`, `patches/ServerTracking.as.inc` et `admin.js`.

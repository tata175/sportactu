# Média auto-mis à jour (gratuit)

Site statique d'actualité (thème sport (actu, événements, résultats)) reconstruit **toutes les heures** par GitHub Actions et hébergé gratuitement sur GitHub Pages.

## Mise en ligne (≈ 15 min)
1. Créez un compte sur github.com, puis un **nouveau dépôt public** (ex. `techactu`).
2. Envoyez-y tous les fichiers de ce dossier (bouton *Add file → Upload files*, y compris le dossier `.github`).
3. Dépôt → **Settings → Pages → Source : GitHub Actions**.
4. Modifiez `config.json` : `base_url` (`https://VOTRE-PSEUDO.github.io/techactu`), `site_name`, `publisher_name`, `contact_email`.
5. Onglet **Actions → Mise à jour du site → Run workflow**. Le site apparaît à l'adresse `base_url`.

## Changer de niche
Remplacez la liste `feeds` dans `config.json` par les flux RSS de médias de votre thème (adresse du site + `/feed`, ou cherchez « RSS » dans le pied de page). Un flux en erreur est simplement ignoré.

## Synthèse IA (optionnelle, payante, quelques centimes/jour)
Ajoutez le secret `ANTHROPIC_API_KEY` (Settings → Secrets → Actions) et passez `ai_digest.enabled` à `true` : une rubrique « Le point sport du jour » originale, signalée comme générée par IA, s'affiche en haut.

## Publicité
- Vous pouvez demander **Google AdSense** une fois le site en ligne, avec un nom de domaine à vous (~10 €/an ; le sous-domaine github.io est en général refusé).
- Une fois approuvé, mettez votre identifiant (`ca-pub-XXXX`) dans `adsense_publisher_id` : les emplacements pub et `ads.txt` sont générés.
- Dans l'UE, un bandeau de consentement cookies certifié est obligatoire (Google propose un outil gratuit dans AdSense > Confidentialité et messagerie).

## Test local
`python generate.py --demo` (aucune dépendance, Python 3 suffit).

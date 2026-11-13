# RIKA pour Home Assistant

Intégration Home Assistant pour piloter un poêle à granulés RIKA équipé du
module Firenet, à travers le compte [rika-firenet.com](https://www.rika-firenet.com).

Développée et vérifiée sur un RIKA SUMO (carte mère 2.29). Elle n'est pas
affiliée à RIKA et ne change rien aux sécurités du poêle : elle envoie les
mêmes réglages que le site.

## Ce qu'elle apporte

| Entité | Rôle |
| --- | --- |
| Thermostat | Marche/arrêt, mode (Manuel, Auto, Confort), consigne de 14 à 28 °C |
| Interrupteur Marche/arrêt | Allume ou éteint le poêle |
| Interrupteur Plages de chauffe | Suit ou ignore le programme hebdomadaire |
| Interrupteur Hors-gel | Active la protection hors-gel |
| Puissance de chauffe | 30 à 100 %, par pas de 5 |
| Température réduite | 12 à 20 °C, appliquée hors des plages de chauffe |
| Température hors-gel | 4 à 10 °C |
| Plages de chauffe | Deux plages par jour, à écrire `06:00-08:30` ; vide = plage inutilisée |
| Capteurs | État, température de la pièce et de la flamme, granulés consommés, granulés avant entretien, durée de fonctionnement, allumages, code d'erreur, signal Wi-Fi |
| Capteurs binaires | Problème, porte, couvercle à granulés, connexion |

### Les modes

- **Manuel** : le poêle chauffe à la puissance choisie.
- **Auto** : comme Manuel, mais seulement pendant les plages de chauffe.
- **Confort** : le poêle suit la consigne de température.

Régler une température sur le thermostat passe le poêle en mode Confort, le
seul où la consigne est suivie.

## Installation

Avec [HACS](https://hacs.xyz) : menu ⋮ → Dépôts personnalisés, ajoutez
`https://github.com/ylascaux/ha-rika` en catégorie Intégration, téléchargez
« RIKA », puis redémarrez Home Assistant.

À la main : copiez `custom_components/rika` dans le dossier
`custom_components` de votre configuration, puis redémarrez.

Ensuite : Paramètres → Appareils et services → Ajouter une intégration →
**RIKA**, et saisissez l'email et le mot de passe de rika-firenet.com.

## À savoir

- Tout passe par le cloud RIKA : sans Internet ou si le service est en panne,
  le poêle n'est plus pilotable depuis Home Assistant.
- L'état est relu toutes les 30 secondes. Une commande s'affiche tout de suite,
  mais le poêle peut mettre un moment à l'appliquer.
- Les options MultiAir, four et bûches ne sont pas gérées.

## Développement

```sh
uv venv && uv pip install pytest-homeassistant-custom-component
.venv/bin/python -m pytest
```

## Remerciements

Le fonctionnement du cloud RIKA a été compris grâce à
[rika-firenet-custom-component](https://github.com/antibill51/rika-firenet-custom-component).

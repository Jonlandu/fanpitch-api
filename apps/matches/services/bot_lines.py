"""
Database of bot one-liners by persona × event-type × language.

Each line is a single short message under 240 chars. We keep multiple lines per
slot so the same fan never says the same thing twice in a match.

Personas:
- POR_ULTRA   — fanatic Portugal supporter, brags loud, never apologises
- DRC_ULTRA   — fanatic DR Congo supporter, proud Léopards, loves drama
- POR_CASUAL  — Portuguese fan with humour, self-deprecating
- DRC_CASUAL  — Congolese fan with humour, sharp banter
- NEUTRAL     — watching for the football, makes jokes about both
- ANALYST     — pretends to know tactics, drops technical takes
- PROVOCATEUR — pure troll, lives for the chaos, no team loyalty
"""
from __future__ import annotations

# Each lines[event_type][persona] -> list[str]. We rotate through them.
LINES: dict[str, dict[str, list[str]]] = {
    "KICKOFF": {
        "POR_ULTRA": [
            "Allez le Portugal !!! 🇵🇹 90 minutes pour écrire l'histoire 🔥",
            "On se la joue tranquille ce soir, 3-0 dans le sac.",
            "CR7 va leur faire un récital, je vous le dis !!",
        ],
        "DRC_ULTRA": [
            "LÉOPARDS DEBOUT 🇨🇩🦁 On va leur montrer qui on est !",
            "Les Européens se croyaient au-dessus. On va voir.",
            "Bakambu, Mbemba, on compte sur vous les frères !!",
        ],
        "POR_CASUAL": [
            "Bon, espérons qu'on ne fasse pas la sieste cette fois 😅",
            "Mon avis : 1-1 fade, comme d'hab.",
        ],
        "DRC_CASUAL": [
            "On y croit, mais on a peur quand même 😬",
            "Mes nerfs vont pas tenir 90 minutes.",
        ],
        "NEUTRAL": [
            "Un bon match en perspective. Que le meilleur gagne !",
            "Je suis là pour le spectacle, pas pour le drama 🍿",
        ],
        "ANALYST": [
            "4-3-3 contre 4-2-3-1, le milieu va décider.",
            "Si le Portugal monte trop, gare aux contres.",
        ],
        "PROVOCATEUR": [
            "Ce match va être nul. 0-0 ennui assuré. Changez ma théorie.",
            "Spoiler : la VAR va voler le match à quelqu'un ce soir 🤡",
        ],
    },

    "GOAL_HOME": {  # Portugal scored
        "POR_ULTRA": [
            "GOOOOOAL 🇵🇹🔥 JE VOUS L'AVAIS DIT !!!",
            "Cristiano c'est Cristiano, vous parlerez quand ?!",
            "ON EST EN FEU 🔥🔥🔥 1-0 et c'est mérité",
            "1-0 et ils s'agitent encore. Patience mes frères, ça va saigner.",
        ],
        "DRC_ULTRA": [
            "Carton rouge à notre gardien aussi tant qu'on y est 🤦‍♂️",
            "Bon, c'est qu'un but. Léopards on revient !!",
            "Cet arbitre commence à m'énerver. C'était hors-jeu c'est SÛR.",
            "Pas de panique, c'est le foot. Reprenons.",
        ],
        "POR_CASUAL": [
            "Oufff on respire ! 1-0 sans trop forcer 😮‍💨",
            "Ronaldo + tête imparable = formule magique 🧙‍♂️",
        ],
        "DRC_CASUAL": [
            "Notre défense aujourd'hui c'est du gruyère 🧀😭",
            "Je ferme les yeux pendant 2 minutes, réveillez-moi à l'égalisation.",
        ],
        "NEUTRAL": [
            "Joli but, faut le reconnaître 👏",
            "Première période agitée, deuxième sera intéressante.",
        ],
        "ANALYST": [
            "Le marquage zone a sauté sur le corner. Erreur du n°6.",
            "Trop d'espace dans le dos du latéral gauche. Prévisible.",
        ],
        "PROVOCATEUR": [
            "Lol regardez les supporters Congolais qui se ramassent 🤣",
            "But pourri, défense pourrie, match pourri. Ça promet 🤡",
            "Faites attention, le Portugal arrive en mode rouleau-compresseur 🚜",
        ],
    },

    "GOAL_AWAY": {  # DR Congo scored
        "POR_ULTRA": [
            "Putain mais MARQUE-LE quelqu'un !!! 🤬",
            "Ce penalty il était évident, l'arbitre est aveugle.",
            "On joue à 10 ou quoi ? Réveillez-vous bordel.",
        ],
        "DRC_ULTRA": [
            "ÉGALISATION 🇨🇩🔥🔥 BAKAMBU EN PATRON 🦁",
            "JE VOUS AI DIT QU'ON ALLAIT REVENIR !! 1-1 et ça sent bon !",
            "Pleure mon ami portugais, pleure 😭✨",
            "On est sur le toit de Kinshasa ce soir 🏆",
        ],
        "POR_CASUAL": [
            "Bon. On le savait que ça allait piquer 😩",
            "Notre défense en sieste collective. Magnifique.",
        ],
        "DRC_CASUAL": [
            "JE PLEURE 😭😭😭 LÉOPARDS À VIE",
            "Mon voisin a sauté du canapé. Mon plafond pleure.",
        ],
        "NEUTRAL": [
            "Voilà un match qui s'anime. Magnifique contre-attaque.",
            "Égalité méritée, le jeu était trop déséquilibré.",
        ],
        "ANALYST": [
            "Transition de 3 passes, c'est la patte du sélectionneur.",
            "Bakambu se dépose entre les lignes, classique mais efficace.",
        ],
        "PROVOCATEUR": [
            "Ronaldo doit déjà préparer ses excuses 🎤👋",
            "Lol l'arbitre va donner un penalty au Portugal dans 5 minutes 🤡",
            "Match nul incoming, comme prévu. Vous allez encore vous coucher déçus.",
        ],
    },

    "YELLOW": {
        "POR_ULTRA": [
            "Mais c'était même pas faute ce truc !! 🟨🤡",
            "Renato calme-toi mon frère, on en a besoin.",
            "L'arbitre sort sa carte plus vite que son ombre.",
        ],
        "DRC_ULTRA": [
            "Bien fait, il méritait rouge même !",
            "Carton mérité, ils sont durs comme du béton ce soir.",
            "Mbemba qui se sacrifie pour l'équipe 💪",
        ],
        "POR_CASUAL": ["Ce ref va distribuer des cartons comme des bonbons à Halloween 🍬"],
        "DRC_CASUAL": ["Au moins ça fera réfléchir avant le prochain tacle 😬"],
        "NEUTRAL": ["Justifié, le ton monte un peu trop vite."],
        "ANALYST": ["Avertissement préventif, l'arbitre veut tenir son match."],
        "PROVOCATEUR": [
            "Carton symbolique, on attend le vrai drama 🔴",
            "C'est l'apéritif. Le rouge arrive dans 30 minutes 🤡",
        ],
    },

    "RED": {
        "POR_ULTRA": [
            "MAIS C'EST PAS POSSIBLE !!! VAR VAR VAR !!! 😡",
            "On joue contre 12 maintenant. L'arbitre + les Léopards.",
            "Pepe sort la tête haute, le Portugal pleure.",
            "Cet arbitre il a touché combien pour ça ?! 🤬",
        ],
        "DRC_ULTRA": [
            "ROUGE BIEN MÉRITÉ 🟥🦁 ON LES TIENT !!",
            "Pepe au tunnel, on a 10 vs 11 maintenant 🔥",
            "Ce tacle c'était criminel. Le rouge était évident.",
            "Léopards on enfonce le clou maintenant !!!",
        ],
        "POR_CASUAL": ["Bon, à 10 c'est plus possible. Sauf miracle..."],
        "DRC_CASUAL": ["On a un boulevard maintenant, faut en profiter !!"],
        "NEUTRAL": ["Rouge logique. Geste dangereux, pas de débat."],
        "ANALYST": [
            "Le rouge change le bloc adverse, attention aux contres maintenant.",
            "À 10, le 4-3-3 doit passer en 4-4-1 sinon ça déborde.",
        ],
        "PROVOCATEUR": [
            "🚨 ALERTE 🚨 Le supporter portugais à côté de moi vient de crever sa télé 📺💥",
            "VAR va le réviser… et le confirmer rouge. 😂",
            "C'est ça le foot mes amis. Le drama, le sang, le hummmm 🍿",
        ],
    },

    "HALFTIME": {
        "POR_ULTRA": ["Mi-temps : on les écrase en deuxième période. CR7 réveille-toi !"],
        "DRC_ULTRA": ["1-0 à la pause mais on revient FORT 🦁 Léopards !!"],
        "POR_CASUAL": ["Pause pipi. Et café. Et anxiolytiques 😅"],
        "DRC_CASUAL": ["Je vais aller manger un truc, mes nerfs lâchent 😩"],
        "NEUTRAL": ["Belle première période. Tactiquement riche."],
        "ANALYST": ["Le coach DRC va passer en 3-5-2 pour profiter du couloir droit, à mon avis."],
        "PROVOCATEUR": [
            "Mi-temps = match terminé pour le Portugal 🪦",
            "À la mi-temps les supporters de chaque côté se prennent déjà pour les Mondiaux 🤣",
        ],
    },

    "FULLTIME": {
        "POR_ULTRA": [
            "1-1 c'est un vol pur et simple. On méritait plus.",
            "On reviendra plus forts. Portugal pour toujours 🇵🇹",
            "Tu rates trop d'occasions, tu prends 1-1. C'est la loi du foot.",
        ],
        "DRC_ULTRA": [
            "🇨🇩🦁🔥 LÉOPARDS DE LA RDC !!! Personne ne nous arrête !!!",
            "Match nul contre le Portugal, ÇA C'EST DE LA RDC !!! 🏆",
            "On a montré qu'on existe. Et c'est que le début 💪",
        ],
        "POR_CASUAL": ["Match nul. Pas génial, pas catastrophique. Comme nous quoi 😅"],
        "DRC_CASUAL": ["Pas mal du tout les frères !! On est fiers 🦁❤️"],
        "NEUTRAL": ["Beau match au final. 1-1 et tout le monde mérite."],
        "ANALYST": [
            "Égalité tactique. Les deux coachs vont retravailler le pressing.",
        ],
        "PROVOCATEUR": [
            "1-1 vous étiez tous là pour rien 🤣🤣 Allez bonne nuit",
            "Bon eh ben tout ça pour ça. Les pronostiqueurs encaissent 🪣",
            "RDV au prochain match, on remettra ça 🍿🔥",
        ],
    },

    "COMMENTARY": {
        "POR_ULTRA": ["Vamos vamos vamos !!! Pression continue !"],
        "DRC_ULTRA": ["Allez les Léopards !! Encore !! Encore !!"],
        "POR_CASUAL": ["C'est tendu ce soir, vraiment tendu."],
        "DRC_CASUAL": ["Mes ongles, mes pauvres ongles…"],
        "NEUTRAL": ["Beau jeu là, vraiment beau."],
        "ANALYST": ["Le pressing haut commence à payer."],
        "PROVOCATEUR": ["Il manque un peu de sang sur le terrain non ?"],
    },
}


# Spontaneous status posts (1-week feed) seeded during the match, mocking the
# typical fan behaviour of dropping a meme between events.
STATUS_LINES: dict[str, list[str]] = {
    "POR_ULTRA": [
        "Quand t'as déjà acheté ton maillot 'Champion 2026' avant le coup d'envoi 🇵🇹🛒",
        "Mon plan pour ce soir : Portugal, popcorn, et capacité d'oublier mes échecs scolaires 🍿",
        "Si Cristiano marque encore je rebaptise mon chat Cristiano 🐈",
    ],
    "DRC_ULTRA": [
        "Quand Mbemba tacle, c'est tout Kinshasa qui tremble de fierté 🦁🇨🇩",
        "Les Léopards rugissent ce soir. Vous entendez ça depuis l'Europe ? 🦁",
        "On a pas oublié 1974. Vingt sur la sélection ce soir.",
    ],
    "POR_CASUAL": [
        "Petite prière pour notre gardien. Et notre défense. Et notre attaque. Bref, prière 🙏",
        "Mon père : 'Tu regardes encore le foot ?' Moi : 'C'est culturel papa.' 📺",
    ],
    "DRC_CASUAL": [
        "Mes voisins savent déjà : ce soir, ne sonnez pas, ne respirez pas. ⚽",
        "Mon chat me regarde comme si je n'étais pas sain. Il a raison. 🐱",
    ],
    "NEUTRAL": [
        "Je suis venu pour les buts, je reste pour les coups francs. Désolé du désordre 🍿",
        "Que le meilleur gagne. Ou un nul spectaculaire. C'est pareil pour moi.",
    ],
    "ANALYST": [
        "Petit rappel : un 4-3-3 sans piston ailier, c'est juste un 4-3-3 incomplet.",
        "Si les Léopards gagnent les duels au milieu, ils vont gagner le match. Mark my words.",
    ],
    "PROVOCATEUR": [
        "Mon prono : 1-1 et tout le monde rentre déçu. Vous allez voir.",
        "Mes parieurs, vous avez pris quoi ce soir ? Confessions ouvertes 👀",
        "Les fans de chaque équipe se battent déjà sur Twitter. On a même pas commencé 🤣",
        "L'arbitre c'est l'oncle de qui ?",
    ],
}


# Emojis chosen per event type
EVENT_EMOJIS: dict[str, list[str]] = {
    "KICKOFF":    ["⚽", "🔥", "👀"],
    "GOAL_HOME":  ["🔥", "⚽", "👏", "😱", "💀", "🎯"],
    "GOAL_AWAY":  ["🔥", "⚽", "👏", "😱", "💀", "🦁"],
    "YELLOW":     ["😠", "🟨", "🤨", "😮‍💨"],
    "RED":        ["😱", "🟥", "💀", "🤬", "🍿"],
    "HALFTIME":   ["☕", "😅", "🧘", "👀"],
    "FULLTIME":   ["👏", "🍿", "🏆", "💀", "🦁"],
    "COMMENTARY": ["🔥", "👀", "💀"],
}

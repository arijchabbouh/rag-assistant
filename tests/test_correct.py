"""build_prompt.correct(): fixes real typos, never rewrites correct French words."""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

if not (ROOT / "chunks.json").exists() or not (ROOT / "embeddings.npy").exists():
    pytest.skip("chunks.json / embeddings.npy missing", allow_module_level=True)

from build_prompt import correct, normalize  # noqa: E402

# Correct French: must come out unchanged. Several of these were damaged by the old rule
# (quel -> que, menu -> ment, anciennes -> antennes, avant -> ayant, faut -> fait, change -> charge...).
NORMAL_QUESTIONS = [
    "quel est le menu de la cantine",
    "quelles étaient les anciennes options avant 2026",
    "quelles sont les options en 3ème année informatique ?",
    "Quel est le coefficient du cours de Lean Management dans l'option Qualité et Maintenance ?",
    "quel est le pourcentage de la note de stage ?",
    "Quel niveau de langue faut-il justifier pour avoir le diplôme ?",
    "Quels documents faut-il fournir pour obtenir une attestation de départ ?",
    "J'ai réussi après le rattrapage, est-ce que ça change mon rang dans la promotion ?",
    "Que se passe-t-il si mon stage d'été n'est pas accepté par le jury ?",
    "Les matières notées uniquement en TP ont-elles un rattrapage ?",
    "Combien de professeurs composent le jury du PFE ?",
    "Est-ce qu'il y a un examen écrit en DevOps en troisième année informatique ?",
    "Quelles entreprises accueillent les stagiaires du département informatique ?",
    "Est-ce qu'un certificat médical suffit pour justifier mes absences ?",
    "Le rapport de PFE peut-il être confidentiel ?",
    "Combien d'heures dure le cours de Web Basics ?",
    "Quelle est la durée maximale de la prolongation de scolarité accordée à un élève ?",
    "le cours de linux embarqué c'est noté comment",
    "quand est ce que les étudiants visitent les entreprises",
    "Est-ce que je peux changer de filière après la première année ?",
    "Où se trouve la bibliothèque et quels sont ses horaires ?",
    "Comment faire une demande de bourse ?",
    "Qui contacter pour un problème d'emploi du temps ?",
    "Je voudrais savoir quand commencent les vacances d'hiver",
    "Est-ce que les cours du samedi sont obligatoires ?",
    "Peut-on refaire un examen raté pendant la session de rattrapage ?",
    "Mon ami dit que la soutenance aura lieu plus tôt cette année, c'est vrai ?",
    "Faut-il rendre le rapport avant ou après la soutenance ?",
    "Quel est le prix de l'inscription ?",
    "Le club robotique recrute-t-il des membres ?",
    "Comment obtenir une attestation de présence ?",
    "Quelles sont les règles en cas de retard à un examen ?",
    "Combien de temps dure le stage ouvrier ?",
    "Est-ce que les notes sont publiées en ligne ?",
    "Qui signe la convention de stage ?",
    "Puis-je faire mon stage à l'étranger ?",
    "Est-ce que le transport est gratuit pour les élèves ?",
    "Où trouver le planning des devoirs surveillés ?",
    "Quelles matières sont enseignées en anglais ?",
    "Quand faut-il choisir son parcours ?",
]

# Real typing mistakes: missing accents, a letter missing, swapped or wrong.
# Not here: "semstre", which the calendar itself writes ("Examens TP semstre 1"), so it is a document word;
# and singular/plural ("infotronique" -> "infotroniques"), which is no longer "fixed" (another form of a word).
TYPOS = [
    ("quel est le poucentage du stage", "quel est le pourcentage du stage"),
    ("quand est le foum des entreprises", "quand est le forum des entreprises"),
    ("delai remise notes cc s2", "délai remise notes cc s2"),
    ("coef IA 2eme annee info", "coef IA 2ème année info"),
    ("dates du calendier", "dates du calendrier"),
    ("combien d'absnces par semestre", "combien d'absences par semestre"),
    ("date de la soutenence", "date de la soutenance"),
    ("le coeficient du cours", "le coefficient du cours"),
    ("signer la convension de stage", "signer la convention de stage"),
    ("liste des matieres du S1", "liste des matières du S1"),
    ("session de rattrapge", "session de rattrapage"),
    ("reglement des examens", "règlement des examens"),
    ("date limite d'inscripion", "date limite d'inscription"),
]


@pytest.mark.parametrize("question", NORMAL_QUESTIONS)
def test_correct_french_is_left_alone(question):
    assert correct(normalize(question)) == normalize(question)


@pytest.mark.parametrize("typed, expected", TYPOS)
def test_typos_are_fixed(typed, expected):
    assert correct(normalize(typed)) == expected


def test_there_are_40_normal_questions():
    assert len(NORMAL_QUESTIONS) == 40

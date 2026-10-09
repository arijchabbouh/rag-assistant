# Interview Q&A

Model answers. Rewrite each one in your own words before the interview.

## Evaluation

### How did you evaluate your RAG system? / Comment as-tu évalué ton système RAG ?

**EN** — I wrote 52 questions by hand. For each one I recorded which file holds the answer and a piece of
text that the right chunk must contain. A script runs the retrieval for every question and computes hit@k
(is the right chunk in the top k?) and MRR (the average of 1/rank). I tag questions by type, so I can see
that questions worded like the documents score 100% hit@8 while paraphrases score 75%. I only evaluate
retrieval for now; the generated answers are not scored yet.

**FR** — J'ai écrit 52 questions à la main. Pour chacune, j'ai noté le fichier qui contient la réponse et
un bout de texte que le bon chunk doit contenir. Un script lance la recherche pour chaque question et
calcule hit@k (le bon chunk est-il dans les k premiers ?) et le MRR (la moyenne de 1/rang). Les questions
sont classées par type : celles formulées comme les documents obtiennent 100 % de hit@8, les
reformulations 75 %. Pour l'instant je n'évalue que la recherche, pas les réponses générées.

### What is the difference between hit@k and MRR? / Quelle différence entre hit@k et MRR ?

**EN** — hit@k is yes or no: the right chunk is in the top k or it is not. It tells me whether the LLM
receives the information at all. MRR also rewards the position: rank 1 gives 1, rank 2 gives 0.5, rank 4
gives 0.25. Two systems can both have 100% hit@8 and very different MRR. MRR matters because LLMs use the
first excerpts better, and because a good ranking lets me send fewer chunks.

**FR** — hit@k est un oui/non : le bon chunk est dans les k premiers ou pas. Il dit si le LLM reçoit
l'information. Le MRR récompense aussi la position : rang 1 donne 1, rang 2 donne 0,5, rang 4 donne 0,25.
Deux systèmes peuvent avoir 100 % de hit@8 et des MRR très différents. Le MRR compte parce que le LLM
exploite mieux les premiers extraits, et qu'un bon classement permet d'envoyer moins de chunks.

### Did you find a mistake in your own evaluation? / As-tu trouvé une erreur dans ta propre évaluation ?

**EN** — Yes, two. First, my 26 original questions were too close to the documents' wording, so I had 100%
hit@8 and no way to measure an improvement. I added paraphrased, noisy and cross-language questions and the
score fell to 92%. Second, a data leak: my typo fixer built its vocabulary from the documents and also from
the eval questions, so eval questions were never altered while real user questions were. After removing it
I saw that the fixer rewrites valid words such as "Quel" into "Que". The leak was hiding a real bug.

**FR** — Oui, deux. D'abord, mes 26 premières questions étaient trop proches du texte des documents :
100 % de hit@8, donc impossible de mesurer une amélioration. J'ai ajouté des reformulations, des questions
« bruitées » et multilingues, et le score est tombé à 92 %. Ensuite, une fuite de données : mon correcteur
de fautes construisait son vocabulaire à partir des documents mais aussi des questions d'évaluation, donc
ces questions n'étaient jamais modifiées alors que celles des vrais utilisateurs l'étaient. Après l'avoir
enlevée, j'ai vu que le correcteur transforme des mots valides comme « Quel » en « Que ». La fuite cachait
un vrai bug.

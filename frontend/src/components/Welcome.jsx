// Example questions, chosen among those checked against the documents (eval set and manual tests).
const SUGGESTIONS = [
  "Quand est le forum des entreprises ?",
  "Combien d'absences sont tolérées par semestre ?",
  "Liste des matières du S1 informatique",
  "Le rapport de PFE peut-il être confidentiel ?",
  "Quelles étaient les anciennes options avant 2026 ?",
];

export default function Welcome({ onPick }) {
  return (
    <section className="welcome" aria-labelledby="welcome-title">
      <h2 id="welcome-title">Bonjour, que voulez-vous savoir ?</h2>
      <p className="welcome-intro">
        Posez une question sur les plans d'études, le calendrier universitaire, le guide de l'élève ingénieur ou les
        stages. Chaque réponse cite le document et la page d'où elle vient.
      </p>
      <h3 className="welcome-subtitle">Quelques exemples</h3>
      <ul className="suggestions">
        {SUGGESTIONS.map((text) => (
          <li key={text}>
            <button type="button" className="suggestion" onClick={() => onPick(text)}>
              {text}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

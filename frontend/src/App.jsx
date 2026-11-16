import { useEffect, useRef, useState } from "react";
import { askQuestion } from "./api.js";
import Composer from "./components/Composer.jsx";
import Turn from "./components/Turn.jsx";
import Welcome from "./components/Welcome.jsx";

let nextId = 1;

// The question sent as `previous` for follow-ups ("et en 2ème année ?"): the last question that
// got an answer, as in the Streamlit app.
function previousQuestion(turns) {
  for (let i = turns.length - 1; i >= 0; i--) {
    if (turns[i].status === "done") return turns[i].question;
  }
  return null;
}

export default function App() {
  // one turn = the student's question + the assistant's reply
  // {id, question, status: "loading" | "done" | "error", answer, sources, error}
  const [turns, setTurns] = useState([]);
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState(false); // the draft replaces the last question
  const [announce, setAnnounce] = useState("");  // read by screen readers
  const controller = useRef(null);
  const composer = useRef(null);
  const bottom = useRef(null);

  const loading = turns.at(-1)?.status === "loading";

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, loading]);

  async function ask(question, history) {
    const id = nextId++;
    const ctrl = new AbortController();
    controller.current = ctrl;
    setTurns([...history, { id, question, status: "loading" }]);
    setAnnounce("Recherche dans les documents officiels…");

    let update;
    try {
      const data = await askQuestion(question, previousQuestion(history), ctrl.signal);
      update = { status: "done", answer: data.answer, sources: data.sources };
      setAnnounce("Réponse reçue.");
    } catch (error) {
      update = { status: "error", error };
      setAnnounce(`${error.title}. ${error.message}`);
    }
    if (controller.current === ctrl) controller.current = null;
    setTurns((current) => current.map((t) => (t.id === id ? { ...t, ...update } : t)));
  }

  function submit(text) {
    const question = text.trim();
    if (!question || loading) return;
    // editing: the new question replaces the last turn, like editing the last message in Claude
    const history = editing ? turns.slice(0, -1) : turns;
    setDraft("");
    setEditing(false);
    ask(question, history);
  }

  function stop() {
    // the browser stops waiting; the server still finishes its current Gemini call
    controller.current?.abort();
  }

  function editLast() {
    const last = turns.at(-1);
    if (!last || loading) return;
    setDraft(last.question);
    setEditing(true);
    // wait for the draft to be rendered, so the cursor goes to the end of the question
    requestAnimationFrame(() => composer.current?.focus());
  }

  function cancelEdit() {
    setEditing(false);
    setDraft("");
    composer.current?.focus();
  }

  function retryLast() {
    const last = turns.at(-1);
    if (last && !loading) ask(last.question, turns.slice(0, -1));
  }

  function newConversation() {
    controller.current?.abort();
    setTurns([]);
    setDraft("");
    setEditing(false);
    composer.current?.focus();
  }

  return (
    <div className="app">
      <header className="header">
        <img className="header-logo" src="/LOGO.jpg" alt="ENICarthage — École Nationale d'Ingénieurs de Carthage" />
        <div className="header-text">
          <h1>Assistant documentaire</h1>
          <p>Réponses tirées des documents officiels de l'école</p>
        </div>
        {turns.length > 0 && (
          <button type="button" className="btn btn-ghost header-new" onClick={newConversation}>
            Nouvelle conversation
          </button>
        )}
      </header>

      <main className="conversation" aria-label="Conversation">
        {turns.length === 0 ? (
          <Welcome onPick={submit} />
        ) : (
          <ol className="turns">
            {turns.map((turn, i) => {
              const isLast = i === turns.length - 1;
              return (
                <Turn
                  key={turn.id}
                  turn={turn}
                  beingEdited={isLast && editing}
                  onEdit={isLast && !loading ? editLast : null}
                  onRetry={isLast && turn.status === "error" ? retryLast : null}
                />
              );
            })}
          </ol>
        )}
        <div ref={bottom} />
      </main>

      <footer className="footer">
        <p className="disclaimer" role="note">
          <span aria-hidden="true">⚠ </span>
          Vérifiez l'information officielle auprès de l'administration en cas de doute.{" "}
          <strong>Ne saisissez pas de données personnelles.</strong>
        </p>
        <Composer
          ref={composer}
          value={draft}
          onChange={setDraft}
          onSubmit={submit}
          onStop={stop}
          loading={loading}
          editing={editing}
          onCancelEdit={cancelEdit}
        />
      </footer>

      <div className="visually-hidden" role="status" aria-live="polite">
        {announce}
      </div>
    </div>
  );
}

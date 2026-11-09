import { useEffect, useId, useRef, useState } from "react";
import { sendFeedback } from "../api.js";

// "Signaler une réponse fausse": optional comment, then POST /feedback.
export default function Feedback({ question, answer }) {
  const [state, setState] = useState("idle"); // idle | open | sending | sent | error
  const [comment, setComment] = useState("");
  const [error, setError] = useState(null);
  const field = useRef(null);
  const fieldId = useId();

  useEffect(() => {
    if (state === "open") field.current?.focus();
  }, [state]);

  async function submit(event) {
    event.preventDefault();
    setState("sending");
    try {
      await sendFeedback(question, answer, comment);
      setState("sent");
    } catch (err) {
      setError(err);
      setState("error");
    }
  }

  if (state === "sent") {
    return (
      <p className="feedback-done" role="status">
        Merci, votre signalement a été enregistré.
      </p>
    );
  }

  if (state === "idle") {
    return (
      <button type="button" className="btn btn-link feedback-open" onClick={() => setState("open")}>
        Signaler une réponse fausse
      </button>
    );
  }

  return (
    <form className="feedback" onSubmit={submit}>
      <label htmlFor={fieldId} className="feedback-label">
        Qu'est-ce qui est faux ? <span className="optional">(facultatif)</span>
      </label>
      <textarea
        id={fieldId}
        ref={field}
        rows={2}
        maxLength={2000}
        value={comment}
        onChange={(event) => setComment(event.target.value)}
        placeholder="Ex : la date indiquée ne correspond pas au calendrier affiché à l'école"
      />
      {state === "error" && (
        <p className="feedback-error" role="alert">
          {error.title} : {error.message}
        </p>
      )}
      <div className="feedback-actions">
        <button type="submit" className="btn btn-primary btn-small" disabled={state === "sending"}>
          {state === "sending" ? "Envoi…" : "Envoyer le signalement"}
        </button>
        <button type="button" className="btn btn-ghost btn-small" onClick={() => setState("idle")}>
          Annuler
        </button>
      </div>
    </form>
  );
}

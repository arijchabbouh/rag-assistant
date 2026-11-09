import { useImperativeHandle, useLayoutEffect, useRef } from "react";

const MAX_LENGTH = 500; // same limit as the API

export default function Composer({ ref, value, onChange, onSubmit, onStop, loading, editing, onCancelEdit }) {
  const textarea = useRef(null);

  // expose focus() to the parent
  useImperativeHandle(ref, () => ({
    focus: () => {
      const el = textarea.current;
      if (!el) return;
      el.focus();
      el.setSelectionRange(el.value.length, el.value.length); // cursor at the end, ready to edit
    },
  }));

  // grow with the text, up to the CSS max-height
  useLayoutEffect(() => {
    const el = textarea.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
    // a scrollbar only once the CSS max-height is reached
    el.style.overflowY = el.scrollHeight > el.clientHeight ? "auto" : "hidden";
  }, [value]);

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      onSubmit(value);
    } else if (event.key === "Escape" && editing) {
      onCancelEdit();
    }
  }

  const empty = value.trim().length === 0;
  const remaining = MAX_LENGTH - value.length;

  return (
    <form
      className={`composer${editing ? " composer-editing" : ""}`}
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(value);
      }}
    >
      {editing && (
        <div className="composer-edit-banner">
          <span>Modification de votre dernière question</span>
          <button type="button" className="btn btn-link" onClick={onCancelEdit}>
            Annuler
          </button>
        </div>
      )}
      <div className="composer-row">
        <label htmlFor="question" className="visually-hidden">
          Votre question
        </label>
        <textarea
          id="question"
          ref={textarea}
          rows={1}
          value={value}
          maxLength={MAX_LENGTH}
          placeholder="Posez votre question…"
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          aria-describedby="composer-hint"
        />
        {loading ? (
          <button type="button" className="btn btn-stop" onClick={onStop}>
            <span className="stop-square" aria-hidden="true" />
            Arrêter
          </button>
        ) : (
          <button type="submit" className="btn btn-primary" disabled={empty}>
            {editing ? "Renvoyer" : "Envoyer"}
          </button>
        )}
      </div>
      <p id="composer-hint" className="composer-hint">
        Entrée pour envoyer, Maj + Entrée pour aller à la ligne
        {remaining <= 100 && <span className="composer-count"> · {remaining} caractères restants</span>}
      </p>
    </form>
  );
}

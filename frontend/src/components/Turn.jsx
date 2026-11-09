import { useEffect, useMemo, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Feedback from "./Feedback.jsx";
import Sources from "./Sources.jsx";

// "[2]" in the answer becomes a link "#cite-2", rendered as a button that opens source 2.
// Numbers without a matching source are left as plain text.
function linkCitations(answer, sources) {
  const known = new Set(sources.map((s) => s.n));
  return answer.replace(/\[(\d+)\](?!\()/g, (match, n) =>
    known.has(Number(n)) ? `[\\[${n}\\]](#cite-${n})` : match,
  );
}

const NO_SOURCES = [];

export default function Turn({ turn, beingEdited, onEdit, onRetry }) {
  const [openSources, setOpenSources] = useState(() => new Set());
  const [focusSource, setFocusSource] = useState(null);
  const sourcesRef = useRef(null);
  const sources = turn.sources || NO_SOURCES;

  const markdown = useMemo(
    () => (turn.status === "done" ? linkCitations(turn.answer, sources) : ""),
    [turn.status, turn.answer, sources],
  );

  // after a citation click: the card is open, now bring it into view and give it the focus
  useEffect(() => {
    if (focusSource == null) return;
    const card = sourcesRef.current?.querySelector(`[data-source="${focusSource}"]`);
    card?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    card?.querySelector("button")?.focus({ preventScroll: true });
    setFocusSource(null);
  }, [focusSource]);

  function openCitation(n) {
    setOpenSources((current) => new Set(current).add(n));
    setFocusSource(n);
  }

  function toggleSource(n) {
    setOpenSources((current) => {
      const next = new Set(current);
      next.has(n) ? next.delete(n) : next.add(n);
      return next;
    });
  }

  const components = {
    a({ href, children }) {
      if (href?.startsWith("#cite-")) {
        const n = Number(href.slice(6));
        const source = sources.find((s) => s.n === n);
        return (
          <button
            type="button"
            className="cite"
            onClick={() => openCitation(n)}
            aria-label={`Source ${n} : ${source.source}, page ${source.page}`}
            title={`${source.source}, page ${source.page}`}
          >
            {n}
          </button>
        );
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      );
    },
    table({ children }) {
      // wide tables scroll sideways instead of breaking the layout on phones
      return (
        <div className="table-wrap" tabIndex={0} role="region" aria-label="Tableau">
          <table>{children}</table>
        </div>
      );
    },
  };

  return (
    <li className={`turn${beingEdited ? " turn-being-edited" : ""}`}>
      <div className="message message-user">
        <h2 className="visually-hidden">Votre question</h2>
        <p className="bubble">{turn.question}</p>
        {onEdit && (
          <button type="button" className="btn btn-link message-action" onClick={onEdit}>
            Modifier
          </button>
        )}
      </div>

      <div className="message message-assistant">
        <h2 className="visually-hidden">Réponse de l'assistant</h2>

        {turn.status === "loading" && (
          <div className="loading">
            <span className="dots" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            <span>
              Consultation des documents officiels…
              <span className="loading-note">Cela peut prendre jusqu'à une minute.</span>
            </span>
          </div>
        )}

        {turn.status === "error" && (
          <div className={`alert alert-${turn.error.kind}`} role="alert">
            <p className="alert-title">{turn.error.title}</p>
            <p>{turn.error.message}</p>
            {onRetry && (
              <button type="button" className="btn btn-ghost" onClick={onRetry}>
                Réessayer
              </button>
            )}
          </div>
        )}

        {turn.status === "done" && (
          <>
            <div className="answer">
              <Markdown remarkPlugins={[remarkGfm]} components={components}>
                {markdown}
              </Markdown>
            </div>
            <Sources
              ref={sourcesRef}
              sources={sources}
              open={openSources}
              onToggle={toggleSource}
            />
            <Feedback question={turn.question} answer={turn.answer} />
          </>
        )}
      </div>
    </li>
  );
}

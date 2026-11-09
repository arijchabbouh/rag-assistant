import { useId } from "react";
import { sourceTitle } from "../sourceTitle.js";

export default function Sources({ ref, sources, open, onToggle }) {
  const baseId = useId();
  if (sources.length === 0) return null;
  return (
    <section className="sources" ref={ref} aria-label="Sources citées">
      <h3 className="sources-title">Sources</h3>
      <ul>
        {sources.map((s) => {
          const isOpen = open.has(s.n);
          const panelId = `${baseId}-source-${s.n}`;
          return (
            <li key={s.n} className={`source${isOpen ? " source-open" : ""}`} data-source={s.n}>
              <button
                type="button"
                className="source-toggle"
                aria-expanded={isOpen}
                aria-controls={panelId}
                onClick={() => onToggle(s.n)}
              >
                <span className="source-n" aria-hidden="true">{s.n}</span>
                <span className="source-doc" title={s.file || s.source}>{sourceTitle(s)}</span>
                <span className="source-page">page {s.page}</span>
                <span className="source-chevron" aria-hidden="true" />
              </button>
              {isOpen && (
                <blockquote id={panelId} className="source-text">
                  {s.text}
                </blockquote>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

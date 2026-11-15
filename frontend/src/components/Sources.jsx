import { useId } from "react";

// One card per document and page; open it to see its excerpts, each with the number cited in the answer.
export default function Sources({ ref, groups, open, onToggle }) {
  const baseId = useId();
  if (groups.length === 0) return null;
  return (
    <section className="sources" ref={ref} aria-label="Sources citées">
      <h3 className="sources-title">Sources</h3>
      <ul>
        {groups.map((g, i) => {
          const isOpen = open.has(g.key);
          const panelId = `${baseId}-group-${i}`;
          const single = g.items.length === 1;
          return (
            <li key={g.key} className={`source${isOpen ? " source-open" : ""}`}>
              <button
                type="button"
                className="source-toggle"
                aria-expanded={isOpen}
                aria-controls={panelId}
                onClick={() => onToggle(g.key)}
              >
                {/* a number here would read as a citation: only for a single excerpt */}
                {single ? (
                  <span className="source-n" aria-hidden="true">{g.items[0].n}</span>
                ) : (
                  <span className="source-stack" aria-hidden="true" />
                )}
                <span className="source-doc" title={g.file}>
                  {g.title}
                </span>
                <span className="source-page">
                  page {g.page}
                  {!single && <span className="source-count"> · {g.items.length} extraits</span>}
                </span>
                <span className="source-chevron" aria-hidden="true" />
              </button>
              {isOpen && (
                <div id={panelId} className="source-body">
                  {g.context && <p className="source-context">{g.context}</p>}
                  <ol className="source-items">
                    {g.items.map((s) => (
                      <li key={s.n} className="source-item" data-source={s.n} tabIndex={-1}>
                        <span className="source-item-n" aria-label={`Extrait ${s.n}`}>
                          {s.n}
                        </span>
                        <span className="source-text">{s.excerpt}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

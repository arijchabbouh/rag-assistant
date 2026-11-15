import { sourceTitle } from "./sourceTitle.js";

// The excerpts cited in one answer, grouped by document and page:
// 25 calendar lines become one card "Calendrier universitaire 2026-2027, page 1 (25 extraits)".
// Each excerpt keeps its number n, so the citation [n] can still open it.
// Groups come in the order of their first citation.
export function groupSources(sources) {
  const groups = [];
  const byKey = new Map();
  for (const s of sources) {
    const file = s.file || s.source;
    const key = `${file}#${s.page}`;
    let group = byKey.get(key);
    if (!group) {
      group = { key, title: sourceTitle(s), file, page: s.page, items: [] };
      byKey.set(key, group);
      groups.push(group);
    }
    group.items.push(s);
  }
  for (const group of groups) {
    const { context, excerpts } = splitCommonStart(group.items.map((s) => s.text));
    group.context = context;
    group.items = group.items.map((s, i) => ({ ...s, excerpt: excerpts[i] }));
  }
  return groups;
}

// The chunks start with the same context ("Calendrier de l'année universitaire 26-27 — 17-nov Forum...",
// "Plan d'études — Formation ... — Semestre 5 — Matière : ..."). Inside a group, the " — " parts that every
// excerpt shares are shown once, above the list, instead of on every line.
function splitCommonStart(texts) {
  if (texts.length < 2) return { context: "", excerpts: texts };
  const parts = texts.map((t) => t.split(" — "));
  let shared = 0;
  while (parts.every((p) => p.length > shared + 1 && p[shared] === parts[0][shared])) shared++;
  return {
    context: parts[0].slice(0, shared).join(" — "),
    excerpts: parts.map((p) => p.slice(shared).join(" — ")),
  };
}

/** The key of the group that holds excerpt n. */
export function groupKeyOf(groups, n) {
  return groups.find((g) => g.items.some((s) => s.n === n))?.key;
}

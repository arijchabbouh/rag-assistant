import html
import random

import config
import os
import streamlit as st

st.set_page_config(page_title="Assistant ENICarthage", page_icon="🎓", layout="centered")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Spectral:wght@500;600&display=swap');

    :root {
        --bordeaux: #7C2340;
        --bordeaux-dark: #591830;
        --blueprint: #2C4A5E;
        --ink: #241A1E;
        --ink-muted: #6B5D5F;
        --paper: #FAF6F0;
        --line: #E7DED3;
        --gold: #9C7A2E;
    }

    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: var(--paper);
    }

    .block-container {
        max-width: 760px;
        padding-top: 2.2rem;
    }

    /* Letterhead header */
    .app-header h1 {
        font-family: 'Spectral', serif;
        font-weight: 600;
        font-size: 2.1rem;
        color: var(--ink);
        margin-bottom: 0.15rem;
    }
    .app-header p {
        color: var(--ink-muted);
        font-size: 0.95rem;
        line-height: 1.5;
        margin-bottom: 0.9rem;
    }
    .app-header hr {
        border: none;
        border-top: 2px solid var(--bordeaux);
        margin: 0 0 1.6rem 0;
    }

    /* Hero (empty state) */
    .hero-intro {
        color: var(--ink-muted);
        font-size: 0.92rem;
        margin: 0.2rem 0 0.8rem 0;
    }

    /* Suggestion chips + all secondary buttons */
    div[data-testid="stButton"] > button,
    button[data-testid="stBaseButton-secondary"] {
        border-radius: 999px;
        border: 1px solid var(--line);
        background-color: #FFFFFF;
        color: var(--ink);
        padding: 0.4rem 0.9rem;
        font-size: 0.88rem;
    }
    div[data-testid="stButton"] > button:hover,
    button[data-testid="stBaseButton-secondary"]:hover {
        border-color: var(--bordeaux);
        color: var(--bordeaux);
    }

    /* Interpreted-search hint */
    .search-hint {
        display: inline-block;
        color: var(--gold);
        font-size: 0.85rem;
        font-style: italic;
        margin-bottom: 0.3rem;
    }

    /* Source citations */
    .sources-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--blueprint);
        letter-spacing: 0.02em;
        margin: 0.8rem 0 0.35rem 0;
    }
    .source-card {
        border-left: 2px solid var(--blueprint);
        padding: 0.15rem 0 0.15rem 0.7rem;
        margin-bottom: 0.55rem;
    }
    .source-card .source-name {
        color: var(--blueprint);
        font-weight: 600;
        font-size: 0.88rem;
    }
    .source-card .source-page {
        color: var(--ink-muted);
        font-size: 0.8rem;
        margin-left: 0.3rem;
    }
    .source-card .source-snippet {
        color: var(--ink-muted);
        font-size: 0.85rem;
        font-style: italic;
        margin: 0.1rem 0 0 0;
        line-height: 1.4;
    }

    /* Chat bubbles: quiet accent instead of heavy card shadows */
    [data-testid="stChatMessage"] {
        border: none;
        background: transparent;
    }
    [data-testid="stChatMessageContent"] {
        border-left: 2px solid var(--line);
        padding-left: 0.8rem;
    }

    @media (max-width: 640px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .app-header h1 { font-size: 1.7rem; }
    }
    </style>
    <div class="app-header">
      <h1> Assistant ENICarthage</h1>
      <p>Répond à partir des documents officiels de l'école (plans d'études, calendrier, guide de l'élève,
      documents de stage), sources à l'appui. Réponses générées par IA : vérifiez auprès de l'administration.
      Une question courte comme « et les DS ? » est comprise avec la question précédente.</p>
      <hr/>
    </div>
    """,
    unsafe_allow_html=True,
)

if not os.environ.get("GEMINI_API_KEY"):
    st.error("La clé GEMINI_API_KEY n'est pas définie. Définissez-la, puis relancez l'application.")
    st.stop()


@st.cache_resource(show_spinner="Chargement du moteur de recherche...")
def load_assistant():
    import ask            # loads the search model and the embeddings once
    import build_prompt
    import followup
    from suggestions import build_suggestions
    return followup, build_prompt, build_suggestions()


assistant, search, suggestions = load_assistant()

if "history" not in st.session_state:
    st.session_state.history = []   # list of (question, hint, answer, sources)


def on_pick():
    """A suggestion was chosen (or a free text was typed and validated): ask it, then clear the box."""
    st.session_state.pending = st.session_state.pick
    st.session_state.pick = None


def ask_now(question_text):
    """A suggestion chip was clicked: ask it directly."""
    st.session_state.pending = question_text


# --- Sidebar: about, session stats, new conversation -----------------------
with st.sidebar:
    st.markdown("### 🎓 ENICarthage")
    st.caption(
        "Assistant documentaire de l'École Nationale d'Ingénieurs de Carthage. "
        "Les réponses s'appuient uniquement sur les documents officiels indexés."
    )
    st.divider()

    n_questions = len(st.session_state.history)
    cited_sources = {
        c["source"] for _, _, _, srcs in st.session_state.history for c in srcs
    }
    col_a, col_b = st.columns(2)
    col_a.metric("Questions posées", n_questions)
    col_b.metric("Documents cités", len(cited_sources))

    st.divider()
    if st.button("🗑️ Nouvelle conversation", use_container_width=True):
        st.session_state.history = []
        st.session_state.pop("hero_chips", None)
        st.rerun()

    st.divider()
    st.caption("Documents couverts : plans d'études, calendrier universitaire, guide de l'élève, stages.")


# --- Empty state: engaging suggestion chips ---------------------------------
if not st.session_state.history:
    if "hero_chips" not in st.session_state:
        categories = {
            "guide de l'élève": [s for s in suggestions if s.startswith("Que dit le guide")],
            "calendrier": [s for s in suggestions if s.startswith("Quand a lieu")],
            "cours": [s for s in suggestions if s.startswith("Combien d'heures")],
            "général": [
                s for s in suggestions
                if not s.startswith(("Que dit le guide", "Quand a lieu", "Combien d'heures"))
            ],
        }
        picks = []
        for pool in categories.values():
            if pool:
                picks.append(random.choice(pool))
        st.session_state.hero_chips = picks[:4]

    st.markdown('<p class="hero-intro">Quelques questions pour commencer :</p>', unsafe_allow_html=True)
    chip_cols = st.columns(2)
    for i, chip in enumerate(st.session_state.hero_chips):
        with chip_cols[i % 2]:
            st.button(chip, key=f"chip_{i}", use_container_width=True, on_click=ask_now, args=(chip,))

with st.expander(" Rechercher parmi toutes les questions suggérées"):
    st.selectbox(
        "Commencez à taper : des questions vous sont proposées (ou validez votre propre texte avec Entrée)",
        options=suggestions,
        index=None,
        placeholder="Ex : web basics, stage, absences, examen...",
        accept_new_options=True,
        key="pick",
        on_change=on_pick,
    )


def snippet(chunk):
    """The cited line itself, so the answer can be checked without opening the PDF."""
    text = chunk["text"].split(" — ")[-1].replace("\n", " ").strip()
    return text[:110] + ("…" if len(text) > 110 else "")


def show(answer, sources, hint):
    if hint:
        st.markdown(f'<span class="search-hint">Recherche interprétée comme : « {html.escape(hint)} »</span>', unsafe_allow_html=True)
    st.write(answer)
    if sources:
        st.markdown('<p class="sources-title">Sources</p>', unsafe_allow_html=True)
        for c in sources:
            st.markdown(
                f"""<div class="source-card">
                    <span class="source-name">{html.escape(str(c['source']))}</span>
                    <span class="source-page">page {html.escape(str(c['page']))}</span>
                    <p class="source-snippet">{html.escape(snippet(c))}</p>
                </div>""",
                unsafe_allow_html=True,
            )


for q, hint, answer, sources in st.session_state.history:
    with st.chat_message("user"):
        st.write(q)
    with st.chat_message("assistant"):
        show(answer, sources, hint)

typed = st.chat_input("Ou écrivez directement votre question ici")
question = st.session_state.pop("pending", None) or typed
if question:
    previous = st.session_state.history[-1][0] if st.session_state.history else None
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        # show what the search understood when typos or accents were fixed
        normalized = search.normalize(question)
        fixed = search.correct(normalized)
        hint = fixed if fixed != normalized else None
        with st.spinner("Consultation des documents officiels..."):
            try:
                answer, sources = assistant.ask_with_context(question, previous)
            except Exception as e:
                st.error(getattr(e, "user_message", f"Une erreur est survenue ({type(e).__name__}). Réessayez dans un instant."))
                st.stop()
        show(answer, sources, hint)
    st.session_state.history.append((question, hint, answer, sources))
    st.rerun()

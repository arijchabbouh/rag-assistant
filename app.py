import config
import os
import streamlit as st

st.set_page_config(page_title="Assistant ENICarthage", page_icon="🎓")
st.title("🎓 Assistant ENICarthage")
st.caption(
    "Répond uniquement à partir des documents de l'école (plans d'études, calendrier, guide de l'élève, "
    "documents de stage), avec les sources. Réponses générées par IA : vérifiez auprès de l'administration. "
    "Une question courte comme « et les DS ? » est comprise avec la question précédente."
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
        st.caption(f"Recherche interprétée comme : « {hint} »")
    st.write(answer)
    if sources:
        st.markdown("**Sources**")
        for c in sources:
            st.markdown(f"- {c['source']} (page {c['page']}) : {snippet(c)}")


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
        with st.spinner("Recherche dans les documents..."):
            try:
                answer, sources = assistant.ask_with_context(question, previous)
            except Exception as e:
                st.error(getattr(e, "user_message", f"Une erreur est survenue ({type(e).__name__}). Réessayez dans un instant."))
                st.stop()
        show(answer, sources, hint)
    st.session_state.history.append((question, hint, answer, sources))
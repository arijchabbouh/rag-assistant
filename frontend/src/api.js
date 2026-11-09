// Calls to the FastAPI server (api.py). Every error becomes an ApiError with a French message.

export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(kind, title, message) {
    super(message);
    this.kind = kind;    // "quota" | "rate" | "invalid" | "server" | "network" | "aborted"
    this.title = title;
  }
}

function errorFor(status, detail) {
  switch (status) {
    case 503:
      return new ApiError(
        "quota",
        "Quota Gemini atteint ou service indisponible",
        // the API already sends a clear French message for this case
        typeof detail === "string" ? detail : "Le service de génération est momentanément indisponible. Réessayez dans une minute.",
      );
    case 429:
      return new ApiError("rate", "Trop de questions d'affilée", "Vous avez posé plus de 20 questions en une minute. Attendez un peu puis réessayez.");
    case 422:
      return new ApiError("invalid", "Question invalide", "La question doit contenir entre 1 et 500 caractères.");
    default:
      return new ApiError("server", "Erreur du serveur", "Une erreur est survenue côté serveur. Réessayez dans un instant.");
  }
}

async function post(path, body, signal) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err.name === "AbortError") {
      throw new ApiError("aborted", "Génération arrêtée", "Vous avez arrêté la génération de la réponse.");
    }
    throw new ApiError(
      "network",
      "Serveur injoignable",
      `Impossible de contacter l'API (${API_URL}). Vérifiez qu'elle est lancée : uvicorn api:app --port 8000`,
    );
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    // empty or non-JSON body: handled below
  }
  if (!response.ok) throw errorFor(response.status, data?.detail);
  return data;
}

/** POST /ask -> {answer, sources: [{n, source, page, text}], corrected_query} */
export function askQuestion(question, previous, signal) {
  return post("/ask", { question, previous: previous || null }, signal);
}

/** POST /feedback -> {saved: true} */
export function sendFeedback(question, answer, comment) {
  return post("/feedback", { question, answer, comment: comment?.trim() || null });
}

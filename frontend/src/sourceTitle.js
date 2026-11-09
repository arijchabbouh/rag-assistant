// The name shown for a source, in the source cards and on the citations.
// The API sends the document's "titre" (documents_status.json) in `source`, or the file name when the
// document has no title; in that case the file name is made readable:
// "PE_Informatique_Janvier_2026.pdf" -> "PE Informatique Janvier 2026".
export function sourceTitle(source) {
  if (source.file && source.source !== source.file) return source.source;
  return source.source.replace(/\.(pdf|docx)$/i, "").replace(/_+/g, " ").trim();
}

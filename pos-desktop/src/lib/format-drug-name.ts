/**
 * Cosmetic cleanup of SAP material descriptions for cashier-facing display.
 *
 * The raw `pharma.drug_catalog.name_en` field contains heavily abbreviated
 * SAP/EDA descriptors with vendor-specific prefixes/suffixes that are
 * unreadable on the cart and quick-pick tiles:
 *
 *   #$CALDIN-C 30/TAB(NEW)$#
 *   4321MINCEUR TEACTIVE(SLIMMING)20TEA BAG
 *   3238577777 PARACETAMOL 500MG 20/TAB
 *   A.BANDERAS KING OF SEDU.ABS.EDT #F/M100M
 *
 * `cleanDrugName(raw)` applies a conservative regex pass so the *display*
 * looks better while the underlying drug_code (and the data we send to the
 * API) is unchanged. Non-destructive — never drops alphabetic content; only
 * strips obvious junk markers that have no clinical meaning.
 *
 * Cleanup rules (each independent, all applied):
 *   1. Strip a leading numeric prefix of 4+ digits when followed by a
 *      letter/space (e.g. "4321MINCEUR ..." → "MINCEUR ...")
 *   2. Strip "$#" / "#$" / "#F" / "#M" trailing markers and their wrapping
 *      forms ("#$...$#" → "...")
 *   3. Collapse runs of dots/spaces to a single one
 *   4. Trim whitespace
 *
 * Examples:
 *   "#$CALDIN-C 30/TAB(NEW)$#"             → "CALDIN-C 30/TAB(NEW)"
 *   "4321MINCEUR TEACTIVE..."              → "MINCEUR TEACTIVE..."
 *   "3238577777 PARACETAMOL 500MG 20/TAB"  → "PARACETAMOL 500MG 20/TAB"
 *   "A.BANDERAS KING OF SEDU.ABS.EDT"      → unchanged (no junk markers)
 */

export function cleanDrugName(raw: string | null | undefined): string {
  if (!raw) return "";
  let s = String(raw);

  // Strip wrapping #$...$# markers
  s = s.replace(/^#\$/, "").replace(/\$#$/, "");

  // Strip leading hash markers like "#F", "#M" if at very start
  s = s.replace(/^#[A-Z]\s*/, "");

  // Strip trailing hash-prefixed marker tokens (e.g. "#F/M100M") at end
  s = s.replace(/\s*#[A-Z][^\s]*$/, "");

  // Strip a leading numeric prefix of 4+ digits, with or without a separator
  // before the next alphabetic character. e.g. "4321MINCEUR" → "MINCEUR".
  s = s.replace(/^\d{4,}\s*(?=[A-Za-z])/, "");

  // Collapse runs of dots (".." → ".") and runs of spaces.
  s = s.replace(/\.{2,}/g, ".").replace(/\s{2,}/g, " ");

  return s.trim();
}

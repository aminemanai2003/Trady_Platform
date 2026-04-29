/**
 * KYC OCR extraction route — fully local, free, multi-language.
 *
 * Pipeline
 * --------
 *   1. Send image to Django backend (EasyOCR multi-language: EN/FR/AR/...).
 *      Django returns: { raw_ocr_text, first_name, last_name, ... } where the
 *      structured fields are extracted by spatial+regex heuristics.
 *
 *   2. Take the raw_ocr_text and run a SECOND pass with local Ollama
 *      (Qwen 2.5 3B, temperature 0, response_format json_object). The LLM is
 *      much better at parsing messy OCR text into structured fields than
 *      regex — it handles French CNI / Tunisian CIN / passports / CVs.
 *
 *   3. Merge: prefer LLM-extracted fields over Django regex fields, fall back
 *      to regex if the LLM refused or produced an invalid value.
 *
 *   4. Validate, score confidence, return.
 *
 * No external APIs. No paid services. Both Django (EasyOCR) and Ollama
 * (Qwen 2.5 3B) run on the user's machine.
 */

import { NextResponse } from "next/server";

// ── Config ─────────────────────────────────────────────────────────────────

const MAX_FILE_BYTES = 20 * 1024 * 1024; // 20 MB — matches Django backend limit
const MIN_DIMENSION = 500;
const DJANGO_OCR_URL = `${(process.env.DJANGO_API_URL ?? "http://localhost:8000").replace(/\/$/, "")}/api/ocr/extract/`;
const OLLAMA_BASE_URL = process.env.OLLAMA_BASE_URL ?? "http://localhost:11434/v1";
const OCR_REFINER_MODEL = process.env.OLLAMA_INTENT_MODEL ?? "qwen2.5:3b";

// ── Output shape (UI contract — do not break) ──────────────────────────────

type ExtractedIdentity = {
  fullName: string | null;
  cinNumber: string | null;
  nationality: string | null;
  documentCountry: string | null;
  documentType: string | null;
  dateOfBirth: string | null;
  expirationDate: string | null;
  email: string | null;
  phoneNumber: string | null;
  rawText: string | null;
  confidenceBasic: number;
};

const EMPTY_EXTRACTED: ExtractedIdentity = {
  fullName: null,
  cinNumber: null,
  nationality: null,
  documentCountry: null,
  documentType: null,
  dateOfBirth: null,
  expirationDate: null,
  email: null,
  phoneNumber: null,
  rawText: null,
  confidenceBasic: 0,
};

// ── Helpers ────────────────────────────────────────────────────────────────

function clampConfidence(value: number): number {
  return Math.min(1, Math.max(0, Number(value.toFixed(2))));
}

function normalizeText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const cleaned = value.replace(/\s+/g, " ").trim();
  return cleaned.length ? cleaned : null;
}

/**
 * Tolerant JSON extractor — strips code fences and extracts the first
 * `{...}` block. Mirrors the helper used by /api/intent.
 */
function extractJson(raw: string): unknown {
  const trimmed = raw.trim();
  try {
    return JSON.parse(trimmed);
  } catch {
    /* fall through */
  }
  const fenced = trimmed.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/, "");
  try {
    return JSON.parse(fenced);
  } catch {
    /* fall through */
  }
  const match = trimmed.match(/\{[\s\S]*\}/);
  if (match) {
    try {
      return JSON.parse(match[0]);
    } catch {
      return null;
    }
  }
  return null;
}

// ── Step 1: Django EasyOCR ─────────────────────────────────────────────────

interface DjangoOcrResult {
  rawText: string;
  djangoFields: Partial<ExtractedIdentity>;
  baseConfidence: number;
}

async function runDjangoOcr(file: File): Promise<DjangoOcrResult | null> {
  const body = new FormData();
  body.append("image", file, file.name);

  const response = await fetch(DJANGO_OCR_URL, {
    method: "POST",
    body,
    signal: AbortSignal.timeout(60_000),
  });

  if (!response.ok) {
    throw new Error(`Django OCR returned ${response.status}`);
  }

  const data: Record<string, unknown> = await response.json();

  const firstName = normalizeText(data.first_name);
  const lastName = normalizeText(data.last_name);
  const fullName =
    firstName && lastName
      ? `${firstName} ${lastName}`.trim()
      : firstName ?? lastName ?? null;

  const djangoFields: Partial<ExtractedIdentity> = {
    fullName,
    cinNumber: normalizeText(data.id_number),
    nationality: normalizeText(data.nationality),
    documentCountry: null,
    documentType: null,
    dateOfBirth: normalizeText(data.date_of_birth),
    expirationDate: normalizeText(data.expiry_date),
    email: normalizeText(data.email),
    phoneNumber: normalizeText(data.phone),
    rawText: normalizeText(data.raw_ocr_text),
  };

  const baseConfidence =
    typeof data.confidence === "number" ? clampConfidence(data.confidence) : 0;

  return {
    rawText: typeof data.raw_ocr_text === "string" ? data.raw_ocr_text : "",
    djangoFields,
    baseConfidence,
  };
}

// ── Step 2: Ollama structured extraction ───────────────────────────────────

const OLLAMA_SYSTEM_PROMPT = `You extract identity fields from raw OCR text of an ID card, passport, residence permit, or similar. The OCR is messy: typos, awkward line breaks, mixed scripts, label fragments.

Output ONE JSON object, exactly this schema and nothing else:

{
  "fullName": string | null,
  "cinNumber": string | null,
  "nationality": string | null,
  "documentCountry": string | null,
  "documentType": string | null,
  "dateOfBirth": "YYYY-MM-DD" | null,
  "expirationDate": "YYYY-MM-DD" | null,
  "email": string | null,
  "phoneNumber": string | null
}

ABSOLUTE RULES (no exceptions):
1. Output JSON only. No prose, no markdown, no code fences.
2. NEVER copy a label as a value. The following are LABELS, never values:
   NOM, Surname, Prénoms, Prenoms, "Given names", "Ghen names", Nationalité,
   Nationalite, "Matanatty", Sex, Sexe, "Date de naissance", "DATE DENAISS",
   "Daledot", "Date of birth", "Lieu de naissance", "Place of birth",
   "N° du document", "Document No.", "Doal", "Expiry date", "Date d'expiration",
   "Alternate name", "Alchnate name", "République Française", "Identity Card",
   Signature, Sonatuse, FR.
3. fullName = "<Given Names> <SURNAME>" — concatenate ONLY the actual name strings.
   Example: NOM="MARTIN", Prénoms="Maëlys-Gaëlle, Marie" → "Maëlys-Gaëlle, Marie MARTIN".
   Do NOT include the words "Given names", "DATE DENAISS", or any other label.
   If you cannot cleanly identify both, return null.
4. cinNumber = the alphanumeric document number (e.g. "X4RTBPFW4", "12345678").
   It is NOT the signature serial (small number bottom-right like "384213").
5. nationality: adjective form in English (FRA→"French", TUN→"Tunisian", DEU→"German",
   USA→"American", GBR→"British"). 3-letter ISO codes ALWAYS map this way.
6. documentCountry: English country name ("France", "Tunisia", "Germany").
7. documentType: pick the ONE best match: "Identity card", "Passport",
   "Residence permit", "Driver license", "CV", "Resume", "Other".
8. DATES — CRITICAL:
   - On French/EU ID cards dates are written DAY MONTH YEAR (DD MM YYYY).
     "13 07 1990" → "1990-07-13".  "11 02 2030" → "2030-02-11".
   - The first number is the day (1-31), second is month (1-12), third is year.
   - If the year looks like an OCR misread (e.g. "7990" instead of "1990",
     "0990" instead of "1990") AND the document context makes it obvious
     (e.g. clearly a date of birth → year must be 1900-2010), correct the
     leading digit to the most likely century. "7990" with day/month "13/07"
     on a date-of-birth field → "1990-07-13".
   - If you cannot identify which value is the date with confidence, return null.
   - dateOfBirth is the value next to "DATE DE NAISS" / "Date of birth".
   - expirationDate is the value next to "DATE D'EXPIR" / "Expiry date".
9. email / phoneNumber: only if explicitly printed (rare on ID cards), else null.
10. Any field you are not 100% sure about → null. Do NOT fill from imagination.`;

/**
 * Returns:
 *   - { ran: false, fields: {} } if the refiner could not be reached / returned junk
 *   - { ran: true,  fields }     if the LLM ran cleanly. `fields` may contain
 *                                explicit nulls — those are deliberate and must
 *                                NOT be overridden by Django regex output.
 */
interface RefinerResult {
  ran: boolean;
  fields: Partial<ExtractedIdentity>;
}

// Reject any string that contains a known OCR label fragment — these are NEVER
// real values, and the LLM occasionally leaks them in.
const LABEL_LEAK_PATTERN =
  /\b(NOM|Surname|Prénoms|Prenoms|Given names|Ghen names|Nationalité|Nationalite|Matanatty|SEXE|Sex|DATE DE\s*NAISS|DATE DENAISS|Daledot|Date of birth|Lieu de naissance|Place of birth|N°\s*DU\s*DOCUMENT|N\s*DU\s*DOCUMENT|Document No\.?|Doal|Expiry date|Date d'expiration|Alternate name|Alchnate name|République Française|Identity Card|Sonatuse|Carte Nationale)\b/i;

function looksLikeLabelLeak(value: string): boolean {
  return LABEL_LEAK_PATTERN.test(value);
}

async function refineWithOllama(rawText: string): Promise<RefinerResult> {
  if (!rawText || rawText.trim().length < 5) return { ran: false, fields: {} };

  let response: Response;
  try {
    response = await fetch(`${OLLAMA_BASE_URL}/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(45_000),
      body: JSON.stringify({
        model: OCR_REFINER_MODEL,
        stream: false,
        temperature: 0,
        response_format: { type: "json_object" },
        messages: [
          { role: "system", content: OLLAMA_SYSTEM_PROMPT },
          { role: "user", content: `RAW OCR TEXT:\n${rawText}` },
        ],
      }),
    });
  } catch (err) {
    console.warn("[OCR] Ollama refiner unreachable:", err instanceof Error ? err.message : err);
    return { ran: false, fields: {} };
  }

  if (!response.ok) {
    console.warn(`[OCR] Ollama refiner HTTP ${response.status}`);
    return { ran: false, fields: {} };
  }

  const data = (await response.json().catch(() => null)) as {
    choices?: Array<{ message?: { content?: string } }>;
  } | null;

  const content = data?.choices?.[0]?.message?.content;
  if (typeof content !== "string" || content.length === 0) return { ran: false, fields: {} };

  const parsed = extractJson(content);
  if (!parsed || typeof parsed !== "object") return { ran: false, fields: {} };

  const obj = parsed as Record<string, unknown>;
  const fields: Partial<ExtractedIdentity> = {};

  for (const key of [
    "fullName",
    "cinNumber",
    "nationality",
    "documentCountry",
    "documentType",
    "dateOfBirth",
    "expirationDate",
    "email",
    "phoneNumber",
  ] as const) {
    if (!(key in obj)) continue; // missing key → leave undefined so Django can fill it
    const v = obj[key];
    if (v === null) {
      fields[key] = null;
      continue;
    }
    if (typeof v !== "string") {
      fields[key] = null;
      continue;
    }
    const cleaned = normalizeText(v);
    if (!cleaned) {
      fields[key] = null;
      continue;
    }
    // Reject label leaks for any text field
    if (looksLikeLabelLeak(cleaned)) {
      console.warn(`[OCR] LLM ${key} rejected (label leak): ${cleaned.slice(0, 80)}`);
      fields[key] = null;
      continue;
    }
    fields[key] = cleaned;
  }

  return { ran: true, fields };
}

// ── Step 2b: Infer document type from raw text + extracted fields ──────────

/** Keyword-to-document-type rules, ordered by specificity (first match wins). */
const DOC_TYPE_RULES: Array<{
  type: string;
  /** At least ONE keyword from each inner array must appear (AND across arrays, OR within). */
  keywords: string[][];
}> = [
  // ── Identity cards ──────────────────────────────────────────────────────
  {
    type: "Identity card",
    keywords: [
      ["carte nationale", "carte d'identité", "carte d'identite", "national identity",
       "identity card", "بطاقة التعريف", "بطاقة الهوية", "personalausweis",
       "documento di identità", "tarjeta de identidad", "bilhete de identidade",
       "carta d'identità", "nüfus cüzdanı", "kimlik kartı",
       "id card", "carte d’identité"],
    ],
  },
  // Also match: country header + "carte" or CIN-style number pattern
  {
    type: "Identity card",
    keywords: [
      ["république française", "republique francaise", "الجمهورية التونسية",
       "royaume du maroc", "المملكة المغربية", "bundesrepublik"],
      ["carte", "card", "بطاقة", "ausweis"],
    ],
  },
  // ── Passports ───────────────────────────────────────────────────────────
  {
    type: "Passport",
    keywords: [["passport", "passeport", "جواز السفر", "reisepass", "passaporto", "pasaporte"]],
  },
  // ── Residence permits ───────────────────────────────────────────────────
  {
    type: "Residence permit",
    keywords: [
      ["titre de séjour", "titre de sejour", "residence permit", "permesso di soggiorno",
       "aufenthaltstitel", "permiso de residencia", "autorisation de séjour",
       "carte de résident", "carte de resident"],
    ],
  },
  // ── Driver licenses ─────────────────────────────────────────────────────
  {
    type: "Driver license",
    keywords: [
      ["permis de conduire", "driver license", "driver's license", "driving licence",
       "führerschein", "patente di guida", "permiso de conducir", "رخصة القيادة",
       "رخصة السياقة"],
    ],
  },
  // ── CV / Resume ─────────────────────────────────────────────────────────
  {
    type: "CV",
    keywords: [["curriculum vitae", "résumé professionnel", "professional experience",
                "work experience", "education", "skills"]],
  },
];

function inferDocumentType(
  rawText: string,
  fields: Omit<ExtractedIdentity, "confidenceBasic">
): string | null {
  const haystack = rawText.toLowerCase();

  for (const rule of DOC_TYPE_RULES) {
    const allGroupsMatch = rule.keywords.every((group) =>
      group.some((kw) => haystack.includes(kw.toLowerCase()))
    );
    if (allGroupsMatch) return rule.type;
  }

  // Structural fallback: if we have an expiry date + id number + nationality
  // it's almost certainly an identity document (card or passport).
  if (fields.cinNumber && fields.expirationDate && fields.nationality) {
    // MRZ-style lines (two lines of >>>) strongly indicate passport
    if (/[A-Z<]{30,}/.test(rawText)) return "Passport";
    return "Identity card";
  }

  return null;
}

// ── Step 3: Merge Django regex + Ollama LLM (LLM wins) ─────────────────────

function mergeExtractions(
  djangoFields: Partial<ExtractedIdentity>,
  refiner: RefinerResult,
  rawText: string
): ExtractedIdentity {
  const llmFields = refiner.fields;
  const llmRan = refiner.ran;

  const pick = (key: keyof ExtractedIdentity): string | null => {
    const llmVal = llmFields[key];
    // If the LLM ran and explicitly set the field to null, trust it —
    // this means the LLM decided the value is garbage / a label leak.
    if (llmRan && key in llmFields && llmVal === null) return null;
    if (typeof llmVal === "string" && llmVal.trim().length > 0) return llmVal;
    const djangoVal = djangoFields[key];
    if (typeof djangoVal === "string" && djangoVal.trim().length > 0) return djangoVal;
    return null;
  };

  const fields: Omit<ExtractedIdentity, "confidenceBasic"> = {
    fullName: pick("fullName"),
    cinNumber: pick("cinNumber"),
    nationality: pick("nationality"),
    documentCountry: pick("documentCountry"),
    documentType: pick("documentType"),
    dateOfBirth: pick("dateOfBirth"),
    expirationDate: pick("expirationDate"),
    email: pick("email"),
    phoneNumber: pick("phoneNumber"),
    rawText: normalizeText(rawText),
  };

  // ── Smart document-type inference when LLM / Django didn't fill it ──────
  if (!fields.documentType) {
    fields.documentType = inferDocumentType(rawText, fields);
  }

  // Heuristic confidence: count how many key fields are populated.
  // Floor 0.4 if we have raw text (means OCR worked even if extraction was sparse).
  let score = rawText && rawText.trim().length >= 20 ? 0.4 : 0.2;
  if (fields.fullName) score += 0.18;
  if (fields.cinNumber) score += 0.18;
  if (fields.dateOfBirth) score += 0.1;
  if (fields.nationality) score += 0.06;
  if (fields.documentCountry) score += 0.04;
  if (fields.documentType) score += 0.04;
  if (fields.expirationDate) score += 0.05;

  return {
    ...fields,
    confidenceBasic: clampConfidence(score),
  };
}

// ── Route handler ──────────────────────────────────────────────────────────

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const file = formData.get("idCard") as File | null;

    if (!file) {
      return NextResponse.json({ error: "ID card image is required" }, { status: 400 });
    }

    if (!file.type.startsWith("image/")) {
      return NextResponse.json({ error: "Invalid image format" }, { status: 400 });
    }

    if (file.size > MAX_FILE_BYTES) {
      return NextResponse.json({ error: "Image too large (max 20MB)" }, { status: 400 });
    }

    let djangoResult: DjangoOcrResult | null = null;
    let djangoError: string | null = null;

    try {
      djangoResult = await runDjangoOcr(file);
    } catch (err) {
      djangoError = err instanceof Error ? err.message : String(err);
      console.error(`[OCR] Django EasyOCR failed: ${djangoError}`);
    }

    if (!djangoResult) {
      return NextResponse.json({
        extracted: EMPTY_EXTRACTED,
        ocrText: "",
        quality: {
          readableEnough: false,
          note: `OCR backend unavailable: ${djangoError}. Make sure Django is running on ${DJANGO_OCR_URL}.`,
        },
        meta: {
          fileName: file.name,
          fileSize: file.size,
          minDimensionHint: MIN_DIMENSION,
          provider: "none",
        },
      });
    }

    const { rawText, djangoFields, baseConfidence } = djangoResult;

    // LLM refinement — never blocks; if it fails, we keep the Django regex output.
    const refinerResult = await refineWithOllama(rawText);
    const llmF = refinerResult.fields;
    console.log(
      `[OCR] llm.ran=${refinerResult.ran} | django.fullName=${djangoFields.fullName ?? "∅"} | llm.fullName=${llmF.fullName ?? "∅"} | llm.cin=${llmF.cinNumber ?? "∅"} | llm.dob=${llmF.dateOfBirth ?? "∅"}`
    );

    const merged = mergeExtractions(djangoFields, refinerResult, rawText);

    // Boost confidence with the EasyOCR raw confidence (averaged with field-coverage score)
    const finalConfidence = clampConfidence(
      Math.max(merged.confidenceBasic, (merged.confidenceBasic + baseConfidence) / 2)
    );
    merged.confidenceBasic = finalConfidence;

    const readableEnough = Boolean(rawText && rawText.trim().length >= 10);
    const qualityNote = readableEnough
      ? null
      : "Document scanned but no text could be reliably extracted. Try a clearer image (good lighting, no glare, full card in frame).";

    return NextResponse.json({
      extracted: merged,
      ocrText: rawText,
      quality: { readableEnough, note: qualityNote },
      meta: {
        fileName: file.name,
        fileSize: file.size,
        minDimensionHint: MIN_DIMENSION,
        provider: refinerResult.ran ? "easyocr+ollama" : "easyocr",
        refiner: OCR_REFINER_MODEL,
      },
    });
  } catch (error) {
    console.error("[OCR] Unhandled error:", error);
    return NextResponse.json({
      extracted: EMPTY_EXTRACTED,
      ocrText: "",
      quality: {
        readableEnough: false,
        note: "OCR extraction failed unexpectedly. Check the server logs.",
      },
    });
  }
}

/**
 * KYC OCR extraction route.
 *
 * Strategy
 * --------
 * 1. Forward the image to the Django OCR pipeline (preprocessing → EasyOCR → LLM fallback).
 * 2. Map the structured backend response to the shape the registration UI expects.
 * 3. If the Django backend is unreachable, fall back to the Gemini vision API directly.
 *
 * Output shape (always a 200 response)
 * ──────────────────────────────────────
 * {
 *   extracted: { fullName, cinNumber, nationality, documentCountry,
 *                documentType, dateOfBirth, expirationDate,
 *                email, phoneNumber, rawText, confidenceBasic },
 *   ocrText:  string,
 *   quality:  { readableEnough: boolean, note: string | null },
 *   meta:     { provider, model?, fileName, fileSize }
 * }
 */

import { NextResponse } from "next/server";

const MAX_FILE_BYTES = 10 * 1024 * 1024; // 10 MB — matches Django backend limit
// MIN_DIMENSION kept for meta reporting only
const MIN_DIMENSION = 500;

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

function clampConfidence(value: number) {
  return Math.min(1, Math.max(0, Number(value.toFixed(2))));
}

function normalizeText(value: unknown) {
  if (typeof value !== "string") {
    return null;
  }

  const cleaned = value.replace(/\s+/g, " ").trim();
  return cleaned.length ? cleaned : null;
}

function parseJsonCandidate(text: string) {
  const trimmed = text.trim();
  const withoutFence = trimmed
    .replace(/^```json\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/\s*```$/i, "");

  const jsonMatch = withoutFence.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    return null;
  }

  try {
    return JSON.parse(jsonMatch[0]) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function extractLooseIdentity(text: string) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const directValue = (pattern: RegExp) => {
    const match = text.match(pattern);
    return match?.[1]?.trim() ?? null;
  };

  return {
    fullName: directValue(/(?:full name|name)\s*[:\-]\s*(.{2,80})/i) ?? extractName(text),
    cinNumber: directValue(/(?:id number|document number|license number|number|no\.?|n\.?o\.?)\s*[:\-]\s*([A-Z0-9\-]{4,24})/i) ?? extractCIN(text),
    nationality: directValue(/(?:nationality|citizenship)\s*[:\-]\s*([A-Za-z][A-Za-z\s-]{2,40})/i) ?? extractNationality(text),
    documentCountry: directValue(/(?:country|issued by|issuing country)\s*[:\-]\s*([A-Za-z][A-Za-z\s-]{2,40})/i) ?? extractDocumentCountry(text),
    documentType: directValue(/(?:document type|id type|card type)\s*[:\-]\s*([A-Za-z][A-Za-z\s-]{2,40})/i) ?? extractDocumentType(text),
    dateOfBirth: directValue(/(?:date of birth|dob|birth date|born on)\s*[:\-]\s*([0-3]?\d[\/\-.][01]?\d[\/\-.](?:\d{2}|\d{4})|\d{4}[\/\-.][01]?\d[\/\-.][0-3]?\d)/i) ?? extractDateOfBirth(text),
    expirationDate: directValue(/(?:expiry date|expiration date|expires|valid until)\s*[:\-]\s*([0-3]?\d[\/\-.][01]?\d[\/\-.](?:\d{2}|\d{4})|\d{4}[\/\-.][01]?\d[\/\-.][0-3]?\d)/i) ?? extractExpirationDate(text),
    email: directValue(/([\w.+-]+@[\w-]+\.[\w.-]+)/i) ?? extractEmail(text),
    phoneNumber: directValue(/(?:phone|mobile|tel|telephone)\s*[:\-]\s*([+()\d][\d\s().-]{5,})/i) ?? extractPhoneNumber(text),
    rawText: normalizeText(text),
    confidenceBasic: 0,
  };
}

function extractFieldByLabel(lines: string[], labels: RegExp[]) {
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (!labels.some((label) => label.test(line))) {
      continue;
    }

    const inlineValue = line.split(/[:\-]/).slice(1).join(":").trim();
    if (inlineValue) {
      return inlineValue;
    }

    const nextLine = lines[index + 1]?.trim();
    if (nextLine && !labels.some((label) => label.test(nextLine))) {
      return nextLine;
    }
  }

  return null;
}

function extractCIN(text: string) {
  const normalized = text.replace(/\s+/g, " ");
  const labeled = normalized.match(/(?:id|identity|document|card|cin|national id|number|no\.?|n\.?o\.?)\s*[:\-]?\s*([A-Z0-9]{6,20})/i);
  if (labeled?.[1]) {
    return labeled[1];
  }

  const directMatch = normalized.match(/\b[A-Z0-9]{6,20}\b/g);
  return directMatch?.[0] ?? null;
}

function extractNationality(text: string) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const labeled = extractFieldByLabel(lines, [/nationality/i, /citizenship/i, /nationalité/i, /nationalite/i]);
  if (labeled) {
    return labeled;
  }

  const upper = text.toUpperCase();
  if (upper.includes("TUNISIAN") || upper.includes("TUNISIEN") || upper.includes("TUNISIE")) {
    return "Tunisian";
  }
  return null;
}

function extractDocumentCountry(text: string) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const labeled = extractFieldByLabel(lines, [/country/i, /issued by/i, /issuing country/i, /pays/i]);
  if (labeled) {
    return labeled;
  }

  const upper = text.toUpperCase();
  if (upper.includes("TUNISIA") || upper.includes("TUNISIE")) {
    return "Tunisia";
  }
  if (upper.includes("MOROCCO") || upper.includes("MAROC")) {
    return "Morocco";
  }
  if (upper.includes("ALGERIA") || upper.includes("ALGERIE") || upper.includes("ALGÉRIE")) {
    return "Algeria";
  }

  return null;
}

function extractName(text: string) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const labeled = extractFieldByLabel(lines, [/full name/i, /name/i, /surname/i, /given names/i, /first name/i, /last name/i, /nom/i, /prénom/i, /prenom/i]);
  if (labeled) {
    return labeled;
  }

  const candidate = lines.find((line) => {
    const upper = line.toUpperCase();
    return upper.length > 4 && !/(OCCUPATION|PROFESSION|DATE OF BIRTH|DOB|NATIONALITY|COUNTRY|SEX|GENDER|ADDRESS|ID NO|DOCUMENT)/i.test(line);
  });

  return candidate ?? null;
}

function extractDocumentType(text: string) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const labeled = extractFieldByLabel(lines, [/document type/i, /id type/i, /card type/i, /identity card/i, /passport/i, /national id/i]);
  if (labeled) {
    return labeled;
  }

  const upper = text.toUpperCase();
  if (upper.includes("PASSPORT")) {
    return "Passport";
  }
  if (upper.includes("IDENTITY CARD") || upper.includes("ID CARD") || upper.includes("NATIONAL ID")) {
    return "Identity card";
  }

  return null;
}

function extractDateOfBirth(text: string) {
  const match = text.match(/(?:date of birth|dob|birth date|born on|né le|ne le|naissance)\s*[:\-]?\s*([0-3]?\d[\/\-.][01]?\d[\/\-.](?:\d{2}|\d{4})|\d{4}[\/\-.][01]?\d[\/\-.][0-3]?\d)/i);
  return match?.[1] ?? null;
}

function extractExpirationDate(text: string) {
  const match = text.match(/(?:expiry date|expiration date|expires|valid until|date d'expiration)\s*[:\-]?\s*([0-3]?\d[\/\-.][01]?\d[\/\-.](?:\d{2}|\d{4})|\d{4}[\/\-.][01]?\d[\/\-.][0-3]?\d)/i);
  return match?.[1] ?? null;
}

function extractEmail(text: string) {
  const match = text.match(/[\w.+-]+@[\w-]+\.[\w.-]+/i);
  return match?.[0] ?? null;
}

function extractPhoneNumber(text: string) {
  const match = text.match(/(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}(?:[\s.-]?\d{2,4})?/);
  return match?.[0] ?? null;
}

function estimateConfidence(text: string, extracted: Omit<ExtractedIdentity, "confidenceBasic">) {
  let score = 0.3;
  if (text.length > 80) score += 0.2;
  if (extracted.cinNumber) score += 0.15;
  if (extracted.nationality) score += 0.15;
  if (extracted.fullName) score += 0.15;
  if (extracted.documentCountry) score += 0.05;
  if (extracted.email) score += 0.1;
  if (extracted.phoneNumber) score += 0.1;
  return clampConfidence(score);
}

function normalizeExtractedIdentity(value: Record<string, unknown>, ocrText: string): ExtractedIdentity {
  const extracted = {
    fullName: normalizeText(value.fullName),
    cinNumber: normalizeText(value.cinNumber ?? value.idNumber ?? value.documentNumber),
    nationality: normalizeText(value.nationality),
    documentCountry: normalizeText(value.documentCountry ?? value.country),
    documentType: normalizeText(value.documentType ?? value.idType),
    dateOfBirth: normalizeText(value.dateOfBirth ?? value.dob),
    expirationDate: normalizeText(value.expirationDate ?? value.expiryDate),
    email: normalizeText(value.email),
    phoneNumber: normalizeText(value.phoneNumber ?? value.phone),
    rawText: normalizeText(value.rawText),
    confidenceBasic: 0,
  };

  const fallback = {
    fullName: extracted.fullName ?? extractName(ocrText),
    cinNumber: extracted.cinNumber ?? extractCIN(ocrText),
    nationality: extracted.nationality ?? extractNationality(ocrText),
    documentCountry: extracted.documentCountry ?? extractDocumentCountry(ocrText),
    documentType: extracted.documentType ?? extractDocumentType(ocrText),
    dateOfBirth: extracted.dateOfBirth ?? extractDateOfBirth(ocrText),
    expirationDate: extracted.expirationDate ?? extractExpirationDate(ocrText),
    email: extracted.email ?? extractEmail(ocrText),
    phoneNumber: extracted.phoneNumber ?? extractPhoneNumber(ocrText),
    rawText: extracted.rawText ?? normalizeText(ocrText),
    confidenceBasic: 0,
  };

  return {
    ...fallback,
    confidenceBasic: estimateConfidence(ocrText, fallback),
  };
}

async function extractWithGemini(file: File): Promise<{ extracted: ExtractedIdentity; ocrText: string; model: string } | null> {
  const apiKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (!apiKey) {
    return null;
  }

  const model = process.env.GEMINI_MODEL || "gemini-2.0-flash";
  const imageBase64 = Buffer.from(await file.arrayBuffer()).toString("base64");

  const prompt = [
    "You are extracting fields from a document image. The image may be an ID card, CV, resume, certificate, or any similar document.",
    "Return strict JSON only with keys: fullName, cinNumber, nationality, documentCountry, documentType, dateOfBirth, expirationDate, email, phoneNumber, rawText.",
    "If a value is not clearly visible, set it to null.",
    "Prefer the exact visible text over guesses.",
    "If the document is a CV or resume, set documentType to CV or Resume and prioritize fullName, email, and phoneNumber when visible.",
    "If the document is an identity document, prioritize the identity fields.",
    "Put the best readable transcription of the whole document in rawText.",
    "Do not add any extra keys, markdown, or explanation.",
  ].join(" ");

  const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      contents: [
        {
          role: "user",
          parts: [
            { text: prompt },
            {
              inline_data: {
                mime_type: file.type || "image/jpeg",
                data: imageBase64,
              },
            },
          ],
        },
      ],
      generationConfig: {
        temperature: 0,
        responseMimeType: "application/json",
      },
    }),
  });

  if (!response.ok) {
    throw new Error(`Gemini API error: ${response.status}`);
  }

  const data = await response.json();
  const text = data?.candidates?.[0]?.content?.parts
    ?.map((part: { text?: string }) => part.text || "")
    .join("") || "";
  const parsed = parseJsonCandidate(text);
  const normalizedText = normalizeText(text) || (parsed?.rawText ? normalizeText(parsed.rawText) || "" : "");

  const extracted = parsed ? normalizeExtractedIdentity(parsed, text) : normalizeExtractedIdentity(extractLooseIdentity(text), text);

  return {
    extracted,
    ocrText: normalizedText,
    model,
  };
}

// ── Django backend proxy ──────────────────────────────────────────────────────

async function extractViaDjangoBackend(
  file: File,
): Promise<{ extracted: ExtractedIdentity; ocrText: string } | null> {
  const backendUrl = (
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api"
  ).replace(/\/$/, "");

  const body = new FormData();
  body.append("image", file, file.name);

  const response = await fetch(`${backendUrl}/ocr/extract/`, {
    method: "POST",
    body,
    signal: AbortSignal.timeout(60_000), // EasyOCR may take time on first init
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

  const extracted: ExtractedIdentity = {
    fullName,
    cinNumber: normalizeText(data.id_number),
    nationality: normalizeText(data.nationality),
    documentCountry: null, // not yet returned by backend
    documentType: null,
    dateOfBirth: normalizeText(data.date_of_birth),
    expirationDate: normalizeText(data.expiry_date),
    email: normalizeText(data.email),
    phoneNumber: normalizeText(data.phone),
    rawText: normalizeText(data.raw_ocr_text),
    confidenceBasic: clampConfidence(
      typeof data.confidence === "number" ? data.confidence : 0,
    ),
  };

  return { extracted, ocrText: (data.raw_ocr_text as string) || "" };
}

// ── Route handler ─────────────────────────────────────────────────────────────

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
      return NextResponse.json({ error: "Image too large (max 10MB)" }, { status: 400 });
    }

    let provider = "django";
    let model: string | undefined;
    let errorMessage: string | null = null;
    let result: { extracted: ExtractedIdentity; ocrText: string; model?: string } | null = null;

    // ── Primary: Django OCR pipeline (EasyOCR → spatial extraction → LLM fallback)
    try {
      result = await extractViaDjangoBackend(file);
    } catch (backendErr) {
      console.warn(
        "Django OCR backend unavailable, falling back to Gemini vision:",
        backendErr instanceof Error ? backendErr.message : backendErr,
      );

      // ── Fallback: direct Gemini vision API
      try {
        provider = "gemini";
        result = await extractWithGemini(file);
        model = (result as { model?: string } | null)?.model;
      } catch (geminiErr) {
        errorMessage =
          geminiErr instanceof Error ? geminiErr.message : "Unknown OCR error";
        console.error("Gemini fallback also failed:", geminiErr);
      }
    }

    const emptyExtracted: ExtractedIdentity = {
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

    const extractionResult = result ?? { extracted: emptyExtracted, ocrText: "" };

    const readableEnough = Boolean(
      extractionResult.ocrText && extractionResult.ocrText.trim().length >= 10,
    );
    const qualityNote = readableEnough
      ? null
      : errorMessage
        ? `OCR failed: ${errorMessage}`
        : "Document scanned but no text could be reliably extracted. Review fields manually.";

    return NextResponse.json({
      extracted: extractionResult.extracted,
      ocrText: extractionResult.ocrText,
      quality: { readableEnough, note: qualityNote },
      meta: {
        fileName: file.name,
        fileSize: file.size,
        minDimensionHint: MIN_DIMENSION,
        provider,
        ...(model ? { model } : {}),
      },
    });
  } catch (error) {
    console.error("KYC OCR error", error);
    return NextResponse.json({
      extracted: {
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
      },
      ocrText: "",
      quality: {
        readableEnough: false,
        note: "OCR extraction failed unexpectedly. Review fields manually.",
      },
    });
  }
}

import { NextRequest, NextResponse } from "next/server";

const DJANGO = (process.env.DJANGO_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

type VoiceFields = {
    name?: string;
    email?: string;
    phoneNumber?: string;
    country?: string;
    city?: string;
    address?: string;
    profession?: string;
    tradingExperience?: string;
    preferredMarket?: string;
    bio?: string;
    kyc?: {
        fullName?: string;
        cinNumber?: string;
        nationality?: string;
        documentCountry?: string;
        documentType?: string;
        dateOfBirth?: string;
        expirationDate?: string;
    };
};

function clean(value?: string | null) {
    return (value ?? "")
        .replace(/\s+/g, " ")
        .replace(/^[\s:,\-.]+|[\s:,\-.]+$/g, "")
        .trim();
}

function sentenceCase(value: string) {
    return clean(value)
        .replace(/\b\w/g, (letter) => letter.toUpperCase())
        .replace(/\b(Of|And|The|A|An)\b/g, (word) => word.toLowerCase())
        .replace(/^./, (letter) => letter.toUpperCase())
        .trim();
}

function stripLeadingArticle(value: string) {
    return clean(value).replace(/^(a|an|the)\s+/i, "");
}

function normalizeName(value: string) {
    return sentenceCase(value.replace(/\b(my|name|is|email|phone|country|city)\b/gi, ""));
}

function normalizeCountry(value: string) {
    const compact = stripLeadingArticle(value).toLowerCase().replace(/[.,]/g, "");
    const aliases: Record<string, string> = {
        "usa": "United States",
        "u s a": "United States",
        "us": "United States",
        "u s": "United States",
        "united states": "United States",
        "united states of america": "United States",
        "the united states": "United States",
        "the united states of america": "United States",
        "uk": "United Kingdom",
        "u k": "United Kingdom",
    };
    return aliases[compact] || sentenceCase(stripLeadingArticle(value));
}

function normalizeProfession(value: string) {
    return sentenceCase(stripLeadingArticle(value));
}

function normalizeExperience(value: string) {
    const numberWords: Record<string, string> = {
        one: "1",
        two: "2",
        three: "3",
        four: "4",
        five: "5",
        six: "6",
        seven: "7",
        eight: "8",
        nine: "9",
        ten: "10",
    };
    const normalized = stripLeadingArticle(value).toLowerCase().replace(/\b(one|two|three|four|five|six|seven|eight|nine|ten)\b/g, (word) => numberWords[word] || word);
    if (/^\d+\s*(year|years|yr|yrs)$/.test(normalized)) return normalized.replace(/\byrs?\b/, "years");
    return sentenceCase(normalized);
}

function normalizePhone(raw: string) {
    const source = clean(raw);
    const hasSpokenPlus = /\bplus\b/i.test(source) || source.includes("+");
    const digits = source.replace(/\D/g, "");
    if (!digits) return "";

    if (digits.startsWith("216") && digits.length === 11) {
        return `+216-${digits.slice(3, 5)}-${digits.slice(5, 8)}-${digits.slice(8)}`;
    }
    if (digits.startsWith("216") && hasSpokenPlus) {
        return `+${digits}`;
    }
    if (hasSpokenPlus) return `+${digits}`;

    return source
        .replace(/[^\d+]/g, " ")
        .replace(/\s+/g, "-")
        .replace(/^-+|-+$/g, "")
        .replace(/^\+-/, "+");
}

function normalizeMarket(value: string) {
    const fixed = stripLeadingArticle(value)
        .replace(/\b4x\b/gi, "forex")
        .replace(/\bfour x\b/gi, "forex")
        .replace(/\bforeign exchange\b/gi, "forex");
    return sentenceCase(fixed);
}

function normalizeBio(value: string) {
    return clean(value)
        .replace(/\b3d\b/gi, "Trady")
        .replace(/\btrady\b/gi, "Trady");
}

function pick(text: string, patterns: RegExp[]) {
    for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match?.[1]) return clean(match[1]);
    }
    return "";
}

function pickOriginal(original: string, lower: string, patterns: RegExp[]) {
    const value = pick(lower, patterns);
    if (!value) return "";
    const index = original.toLowerCase().indexOf(value.toLowerCase());
    if (index < 0) return sentenceCase(value);
    return clean(original.slice(index, index + value.length));
}

function normalizeEmail(raw: string) {
    let email = raw
        .toLowerCase()
        .replace(/\s+at\s+/g, "@")
        .replace(/\s+dot\s+/g, ".")
        .replace(/\s+period\s+/g, ".")
        .replace(/\s*\.\s*@/g, "@")
        .replace(/@\s*\./g, "@")
        .replace(/\s+/g, "")
        .replace(/[.,;]+$/g, "");
    email = email.replace(/@jmail\.com$/i, "@gmail.com");
    email = email.replace(/@g-mail\.com$/i, "@gmail.com");
    email = email.replace(/@hot-mail\.com$/i, "@hotmail.com");
    return email;
}

function extractFields(transcript: string): VoiceFields {
    const original = clean(transcript);
    const lower = ` ${original.toLowerCase()} `;
    const fields: VoiceFields = { kyc: {} };

    const email = original.match(/[A-Z0-9._%+-]+\s*@\s*[A-Z0-9.-]+\.[A-Z]{2,}/i)?.[0]
        || pick(lower, [
            / email(?: address)? (?:is|as) ([a-z0-9._%+\-\s]+(?:@|\s+at\s+)[a-z0-9.\-\s]+(?:\.|\s+dot\s+|\s+period\s+)[a-z]{2,})[\s.,;]/i,
            / mail(?: address)? (?:is|as) ([a-z0-9._%+\-\s]+(?:@|\s+at\s+)[a-z0-9.\-\s]+(?:\.|\s+dot\s+|\s+period\s+)[a-z]{2,})[\s.,;]/i,
        ]);
    if (email) fields.email = normalizeEmail(email);

    const phone = pickOriginal(original, lower, [
        / phone(?: number)? (?:is|as) ((?:plus\s+)?\+?\d[\d\s().-]{6,}\d)/i,
    ]) || original.match(/(?:\+?\d[\d\s().-]{7,}\d)/)?.[0]
        || pick(lower, [/ phone(?: number)? (?:is|as) ([+\d\s().-]{8,})[\s.,;]/i]);
    if (phone) fields.phoneNumber = normalizePhone(phone);

    fields.name = normalizeName(pickOriginal(original, lower, [
        / my name is ([a-z][a-z\s'-]{1,60}?)(?: and |,|\.| email | phone | country | city | address | profession | i live | i work |$)/i,
        / i am ([a-z][a-z\s'-]{1,60}?)(?: and |,|\.| email | phone | country | city | address | profession |$)/i,
        / name (?:is|as) ([a-z][a-z\s'-]{1,60}?)(?: and |,|\.| email | phone | country | city | address | profession |$)/i,
    ]));

    fields.country = normalizeCountry(pick(lower, [
        / country (?:is|as) ([a-z\s'-]{2,50}?)(?: and |,|\.| city | address | nationality |$)/i,
        / i (?:am from|live in) ([a-z\s'-]{2,50}?)(?: and |,|\.| city | address |$)/i,
    ]));
    fields.city = sentenceCase(pick(lower, [
        / city (?:is|as) ([a-z\s'-]{2,50}?)(?: and |,|\.| address | country |$)/i,
        / based in ([a-z\s'-]{2,50}?)(?: and |,|\.| address | country |$)/i,
    ]));
    fields.address = pickOriginal(original, lower, [
        / address (?:is|as) ([a-z0-9\s,.'#-]{4,120}?)(?: and |\.| profession | work | country | city |$)/i,
        / i live at ([a-z0-9\s,.'#-]{4,120}?)(?: and |\.| profession | work | country | city |$)/i,
    ]);
    fields.profession = normalizeProfession(pick(lower, [
        / profession (?:is|as) ([a-z\s'-]{2,60}?)(?: and |,|\.| trading | market | experience |$)/i,
        / i work as (?:a |an )?([a-z\s'-]{2,60}?)(?: and |,|\.| trading | market | experience |$)/i,
    ]));

    const experience = pick(lower, [
        / trading experience (?:is|as) ([a-z0-9\s+-]{2,80}?)(?: and |,|\.| preferred | market |$)/i,
        / i have ([a-z0-9\s+-]{2,80}?)(?: of )?trading experience/i,
    ]);
    if (experience) fields.tradingExperience = normalizeExperience(experience);
    else if (/ beginner /.test(lower)) fields.tradingExperience = "Beginner";
    else if (/ intermediate /.test(lower)) fields.tradingExperience = "Intermediate";
    else if (/ advanced|professional|expert /.test(lower)) fields.tradingExperience = "Advanced";

    const markets = ["forex", "crypto", "stocks", "indices", "commodities", "gold", "major currencies", "eurusd", "gbpusd", "usdjpy"];
    const market = markets.find((item) => lower.includes(` ${item} `));
    const preferredMarket = pick(lower, [
        / preferred market (?:is|as) ([a-z\s/+-]{2,80}?)(?: and |,|\.| bio |$)/i,
        / preferred market (?:is|as) ([a-z0-9\s/+-]{2,80}?)(?: and |,|\.| bio |$)/i,
        / i trade ([a-z0-9\s/+-]{2,80}?)(?: and |,|\.| bio |$)/i,
    ]) || market || "";
    fields.preferredMarket = normalizeMarket(preferredMarket);

    const bio = pickOriginal(original, lower, [
        / bio (?:is|as) ([\s\S]{12,400})$/i,
        / about me[:,\s]+([\s\S]{12,400})$/i,
    ]);
    if (bio) fields.bio = normalizeBio(bio);

    fields.kyc = {
        fullName: pickOriginal(original, lower, [
            / identity full name (?:is|as) ([a-z][a-z\s'-]{1,80}?)(?: and |,|\.| document | cin | nationality |$)/i,
            / legal name (?:is|as) ([a-z][a-z\s'-]{1,80}?)(?: and |,|\.| document | cin | nationality |$)/i,
        ]),
        cinNumber: pick(original, [
            /(?:cin|identity number|document number|id number)\s*(?:is|as|:)?\s*([A-Z0-9 -]{4,30})/i,
        ]),
        nationality: sentenceCase(pick(lower, [
            / nationality (?:is|as) ([a-z\s'-]{2,50}?)(?: and |,|\.| document |$)/i,
        ])),
        documentCountry: sentenceCase(pick(lower, [
            / document country (?:is|as) ([a-z\s'-]{2,50}?)(?: and |,|\.| document type |$)/i,
        ])),
        documentType: sentenceCase(pick(lower, [
            / document type (?:is|as) ([a-z\s'-]{2,40}?)(?: and |,|\.| date | expiration |$)/i,
        ])),
        dateOfBirth: pick(original, [
            /(?:date of birth|birth date|born on)\s*(?:is|as|:)?\s*([A-Za-z0-9 ,/-]{6,30})/i,
        ]),
        expirationDate: pick(original, [
            /(?:expiration date|expiry date|expires on)\s*(?:is|as|:)?\s*([A-Za-z0-9 ,/-]{6,30})/i,
        ]),
    };

    for (const key of Object.keys(fields) as (keyof VoiceFields)[]) {
        if (key !== "kyc" && typeof fields[key] === "string" && !clean(fields[key] as string)) {
            delete fields[key];
        }
    }
    if (fields.kyc) {
        for (const key of Object.keys(fields.kyc) as (keyof NonNullable<VoiceFields["kyc"]>)[]) {
            if (!clean(fields.kyc[key])) delete fields.kyc[key];
        }
    }
    if (!Object.keys(fields.kyc ?? {}).length) delete fields.kyc;

    return fields;
}

export async function POST(req: NextRequest) {
    try {
        const formData = await req.formData();
        const audio = formData.get("audio");
        if (!(audio instanceof File)) {
            return NextResponse.json({ error: "Audio file is required." }, { status: 400 });
        }

        const upstream = new FormData();
        upstream.append("audio", audio, audio.name || "register-voice.webm");

        const response = await fetch(`${DJANGO}/api/v2/register/voice-transcribe/`, {
            method: "POST",
            body: upstream,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            return NextResponse.json(
                { error: data.error || "Voice transcription failed." },
                { status: response.status },
            );
        }

        const transcript = clean(data.text);
        const fields = extractFields(transcript);
        return NextResponse.json({ transcript, fields });
    } catch (error) {
        return NextResponse.json(
            { error: error instanceof Error ? error.message : "Voice autofill failed." },
            { status: 500 },
        );
    }
}

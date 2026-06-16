"use client";

import { useEffect, useRef, useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
    Eye,
    EyeOff,
    CheckCircle2,
    ScanText,
    ShieldCheck,
    Mail,
    Smartphone,
    Scan,
    ArrowRight,
    Shield,
    Mic,
    Square,
    Sparkles,
    Upload,
    UserCircle,
} from "lucide-react";
import { RBButton, RBCard, RBInput, RBLabel, RBPage } from "@/components/reactbits";
import { ProgressIndicator } from "@/components/ui/progress-indicator";
import { Alert } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import FaceEnrollModal from "@/components/FaceEnrollModal";
import TwoFASetupVerification from "@/components/TwoFASetupVerification";
import { SocialAuthButtons } from "@/components/social-auth-buttons";

type KycExtracted = {
    fullName: string;
    cinNumber: string;
    nationality: string;
    documentCountry: string;
    documentType: string;
    dateOfBirth: string;
    expirationDate: string;
    confidenceBasic: number;
    ocrText: string;
};

type TwoFaMethod = "none" | "email" | "sms" | "face";
type PageStep = "form" | "twofa" | "twofa-verify";
type VoiceState = "idle" | "recording" | "processing" | "review";

type VoiceDraft = {
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
    kyc?: Partial<KycExtracted>;
};

function OptionalMark() {
    return <span className="ml-1 text-[10px] font-medium uppercase tracking-wider text-slate-500">Optional</span>;
}

export default function RegisterPage() {
    const router = useRouter();
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const voiceChunksRef = useRef<Blob[]>([]);
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [profilePicture, setProfilePicture] = useState<File | null>(null);
    const [profilePreview, setProfilePreview] = useState("");
    const [country, setCountry] = useState("");
    const [city, setCity] = useState("");
    const [address, setAddress] = useState("");
    const [profession, setProfession] = useState("");
    const [tradingExperience, setTradingExperience] = useState("");
    const [preferredMarket, setPreferredMarket] = useState("");
    const [bio, setBio] = useState("");
    const [showPw, setShowPw] = useState(false);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [ocrLoading, setOcrLoading] = useState(false);
    const [idCardFile, setIdCardFile] = useState<File | null>(null);
    const [kycConfirmed, setKycConfirmed] = useState(false);
    // 2FA setup state
    const [pageStep, setPageStep] = useState<PageStep>("form");
    const [twoFaMethod, setTwoFaMethod] = useState<TwoFaMethod>("none");
    const [phoneNumber, setPhoneNumber] = useState("");
    const [twoFaLoading, setTwoFaLoading] = useState(false);
    const [twoFaError, setTwoFaError] = useState("");
    const [showFaceModal, setShowFaceModal] = useState(false);
    const [voiceState, setVoiceState] = useState<VoiceState>("idle");
    const [voiceError, setVoiceError] = useState("");
    const [voiceTranscript, setVoiceTranscript] = useState("");
    const [voiceDraft, setVoiceDraft] = useState<VoiceDraft | null>(null);
    const [kycData, setKycData] = useState<KycExtracted>({
        fullName: "",
        cinNumber: "",
        nationality: "",
        documentCountry: "",
        documentType: "",
        dateOfBirth: "",
        expirationDate: "",
        confidenceBasic: 0,
        ocrText: "",
    });

    useEffect(() => {
        if (!profilePicture) {
            setProfilePreview("");
            return;
        }
        const nextPreview = URL.createObjectURL(profilePicture);
        setProfilePreview(nextPreview);
        return () => URL.revokeObjectURL(nextPreview);
    }, [profilePicture]);

    async function processVoiceBlob(blob: Blob) {
        setVoiceState("processing");
        setVoiceError("");
        setVoiceTranscript("");
        setVoiceDraft(null);

        try {
            const formData = new FormData();
            formData.append("audio", blob, "registration-profile.webm");
            const res = await fetch("/api/register/voice-autofill", {
                method: "POST",
                body: formData,
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.error || "Voice autofill failed.");
            }
            setVoiceTranscript(data.transcript || "");
            setVoiceDraft(data.fields || {});
            setVoiceState("review");
        } catch (err) {
            setVoiceError(err instanceof Error ? err.message : "Voice autofill failed.");
            setVoiceState("idle");
        }
    }

    async function startVoiceCapture() {
        if (voiceState === "recording") return;
        setVoiceError("");
        setVoiceTranscript("");
        setVoiceDraft(null);

        if (!navigator.mediaDevices?.getUserMedia) {
            setVoiceError("Your browser does not support microphone recording.");
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const recorder = new MediaRecorder(stream);
            voiceChunksRef.current = [];
            mediaRecorderRef.current = recorder;
            recorder.ondataavailable = (event) => {
                if (event.data.size > 0) voiceChunksRef.current.push(event.data);
            };
            recorder.onstop = () => {
                stream.getTracks().forEach((track) => track.stop());
                const blob = new Blob(voiceChunksRef.current, { type: recorder.mimeType || "audio/webm" });
                void processVoiceBlob(blob);
            };
            recorder.start();
            setVoiceState("recording");
        } catch {
            setVoiceError("Microphone permission was denied or unavailable.");
        }
    }

    function stopVoiceCapture() {
        if (mediaRecorderRef.current?.state === "recording") {
            mediaRecorderRef.current.stop();
        }
    }

    function applyVoiceDraft() {
        if (!voiceDraft) return;
        if (voiceDraft.name) setName(voiceDraft.name);
        if (voiceDraft.email) setEmail(voiceDraft.email);
        if (voiceDraft.phoneNumber) setPhoneNumber(voiceDraft.phoneNumber);
        if (voiceDraft.country) setCountry(voiceDraft.country);
        if (voiceDraft.city) setCity(voiceDraft.city);
        if (voiceDraft.address) setAddress(voiceDraft.address);
        if (voiceDraft.profession) setProfession(voiceDraft.profession);
        if (voiceDraft.tradingExperience) setTradingExperience(voiceDraft.tradingExperience);
        if (voiceDraft.preferredMarket) setPreferredMarket(voiceDraft.preferredMarket);
        if (voiceDraft.bio?.trim()) setBio(voiceDraft.bio);
        if (voiceDraft.kyc) {
            setKycData((prev) => ({
                ...prev,
                fullName: voiceDraft.kyc?.fullName || prev.fullName,
                cinNumber: voiceDraft.kyc?.cinNumber || prev.cinNumber,
                nationality: voiceDraft.kyc?.nationality || prev.nationality,
                documentCountry: voiceDraft.kyc?.documentCountry || prev.documentCountry,
                documentType: voiceDraft.kyc?.documentType || prev.documentType,
                dateOfBirth: voiceDraft.kyc?.dateOfBirth || prev.dateOfBirth,
                expirationDate: voiceDraft.kyc?.expirationDate || prev.expirationDate,
            }));
        }
        setVoiceState("idle");
    }

    function chooseProfilePicture(file?: File | null) {
        if (!file) {
            setProfilePicture(null);
            return;
        }
        if (!file.type.startsWith("image/")) {
            setError("Profile picture must be an image.");
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            setError("Profile picture must be 5 MB or less.");
            return;
        }
        setProfilePicture(file);
    }

    async function runOcr() {
        if (!idCardFile) {
            setError("Upload an ID card image before scanning.");
            return;
        }

        setError("");
        setOcrLoading(true);
        setKycConfirmed(false);

        try {
            const formData = new FormData();
            formData.append("idCard", idCardFile);

            const res = await fetch("/api/kyc/ocr-lite", {
                method: "POST",
                body: formData,
            });

            const data = await res.json();
            if (!res.ok) {
                if (data?.extracted) {
                    setKycData({
                        fullName: data.extracted?.fullName || name,
                        cinNumber: data.extracted?.cinNumber || "",
                        nationality: data.extracted?.nationality || "",
                        documentCountry: data.extracted?.documentCountry || "",
                        documentType: data.extracted?.documentType || "",
                        dateOfBirth: data.extracted?.dateOfBirth || "",
                        expirationDate: data.extracted?.expirationDate || "",
                        confidenceBasic: data.extracted?.confidenceBasic || 0,
                        ocrText: data.ocrText || "",
                    });
                }
                setError(data.error || data.quality?.note || "Document scan failed");
                return;
            }

            setKycData({
                fullName: data.extracted?.fullName || name,
                cinNumber: data.extracted?.cinNumber || "",
                nationality: data.extracted?.nationality || "",
                documentCountry: data.extracted?.documentCountry || "",
                documentType: data.extracted?.documentType || "",
                dateOfBirth: data.extracted?.dateOfBirth || "",
                expirationDate: data.extracted?.expirationDate || "",
                confidenceBasic: data.extracted?.confidenceBasic || 0,
                ocrText: data.ocrText || "",
            });

            if (data.quality?.note) {
                setError(data.quality.note);
            }
        } catch {
            setError("Unable to scan the document right now.");
        } finally {
            setOcrLoading(false);
        }
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        setLoading(true);

        if (password.length < 6) {
            setError("Password must be at least 6 characters long");
            setLoading(false);
            return;
        }

        const formData = new FormData();
        formData.append("name", name);
        formData.append("email", email);
        formData.append("password", password);
        formData.append("phoneNumber", phoneNumber);
        formData.append("country", country);
        formData.append("city", city);
        formData.append("address", address);
        formData.append("profession", profession);
        formData.append("tradingExperience", tradingExperience);
        formData.append("preferredMarket", preferredMarket);
        formData.append("bio", bio);
        formData.append("kyc", JSON.stringify({
            confirmed: kycConfirmed,
            fullName: kycData.fullName,
            cinNumber: kycData.cinNumber,
            nationality: kycData.nationality,
            documentCountry: kycData.documentCountry,
            documentType: kycData.documentType,
            dateOfBirth: kycData.dateOfBirth,
            expirationDate: kycData.expirationDate,
            confidenceBasic: kycData.confidenceBasic,
            ocrText: kycData.ocrText,
        }));
        if (profilePicture) formData.append("profilePicture", profilePicture);

        const res = await fetch("/api/auth/register", {
            method: "POST",
            body: formData,
        });

        const data = await res.json();

        if (!res.ok) {
            setError(data.error || "Registration failed");
            setLoading(false);
            return;
        }

        // Auto sign in after register
        const signInRes = await signIn("credentials", {
            email,
            password,
            redirect: false,
        });

        if (!signInRes?.ok) {
            setLoading(false);
            setError("Account created but sign-in failed. Please log in manually.");
            return;
        }

        // Register in Django to get a token for 2FA enrollment
        try {
            await fetch("/api/django-auth/django-register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
            });
        } catch {
            // Django may be offline; skip 2FA setup silently
        }

        setLoading(false);
        setPageStep("twofa");
    }

    async function handle2FaSetup() {
        if (twoFaMethod === "none") {
            router.push("/dashboard");
            router.refresh();
            return;
        }
        if (twoFaMethod === "face") {
            setShowFaceModal(true);
            return;
        }
        if (twoFaMethod === "sms" && !phoneNumber.trim()) {
            setTwoFaError("Please enter your phone number for SMS 2FA.");
            return;
        }
        setTwoFaError("");
        setTwoFaLoading(true);
        try {
            const res = await fetch("/api/django-auth/2fa-setup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    enabled: true,
                    preferred_method: twoFaMethod,
                    ...(twoFaMethod === "sms" ? { phone_number: phoneNumber } : {}),
                }),
            });
            const data = await res.json();
            if (data.success) {
                // For Face, enrollment modal handles redirect to dashboard
                // For Email/SMS, go to verification step
                if (twoFaMethod === "email" || twoFaMethod === "sms") {
                    setPageStep("twofa-verify");
                } else {
                    // Face method - modal will handle navigation after enrollment
                    // This branch shouldn't normally be reached since Face opens modal
                    router.push("/dashboard");
                    router.refresh();
                }
            } else {
                setTwoFaError(data.message || "2FA setup failed.");
            }
        } catch {
            setTwoFaError("Network error. 2FA not configured.");
        } finally {
            setTwoFaLoading(false);
        }
    }

    // ── 2FA Setup Verification step ────────────────────────────────────────────
    if (pageStep === "twofa-verify") {
        return (
            <RBPage className="flex items-center justify-center p-4">
                <div className="relative z-10 w-full max-w-md">
                    <div className="flex items-center justify-center gap-3 mb-8">
                        <Image src="/logo.png" alt="Trady" width={40} height={40} className="h-10 w-10" priority />
                        <span className="text-xl font-bold text-slate-100">Trady</span>
                    </div>

                    <div className="mb-6">
                        <ProgressIndicator 
                            currentStep={3} 
                            totalSteps={3} 
                            type="numbers" 
                            showLabels 
                            className="justify-center" 
                        />
                    </div>

                    <RBCard className="p-6 md:p-8">
                        <TwoFASetupVerification
                            method={twoFaMethod as "face" | "email" | "sms"}
                            phoneNumber={phoneNumber}
                            onComplete={() => {
                                router.push("/dashboard");
                                router.refresh();
                            }}
                            onSkip={() => {
                                router.push("/dashboard");
                                router.refresh();
                            }}
                        />
                    </RBCard>
                </div>
            </RBPage>
        );
    }

    // ── 2FA Setup step ──────────────────────────────────────────────────────
    if (pageStep === "twofa") {
        return (
            <RBPage className="flex items-center justify-center p-4">
                <div className="relative z-10 w-full max-w-md">
                    <div className="flex items-center justify-center gap-3 mb-8">
                        <Image src="/logo.png" alt="Trady" width={40} height={40} className="h-10 w-10" priority />
                        <span className="text-xl font-bold text-slate-100">Trady</span>
                    </div>

                    <div className="mb-6">
                        <ProgressIndicator 
                            currentStep={2} 
                            totalSteps={3} 
                            type="numbers" 
                            showLabels 
                            className="justify-center" 
                        />
                    </div>

                    <RBCard className="p-6 md:p-8">
                        <div className="flex items-center justify-center w-14 h-14 rounded-full bg-brand-blue-500/15 mx-auto mb-4">
                            <Shield className="size-7 text-brand-blue-400" />
                        </div>
                        <h2 className="text-2xl font-bold text-slate-100 text-center mb-1">Secure your account</h2>
                        <p className="text-sm text-slate-400 text-center mb-6">Choose a two-factor authentication method for your account.</p>

                        {twoFaError && (
                            <Alert variant="error" className="mb-4" onClose={() => setTwoFaError("")}>
                                {twoFaError}
                            </Alert>
                        )}

                        <div className="space-y-3 mb-6">
                            {([
                                { id: "none",  icon: <ArrowRight className="size-5 text-slate-400" />, label: "Skip for now",   desc: "You can enable 2FA later." },
                                { id: "email", icon: <Mail       className="size-5 text-sky-400"   />, label: "Email OTP",      desc: "Receive a code by email at each login." },
                                { id: "sms",   icon: <Smartphone className="size-5 text-violet-400" />, label: "SMS OTP",       desc: "Receive a code by SMS at each login." },
                                { id: "face",  icon: <Scan       className="size-5 text-emerald-400" />, label: "Face ID",      desc: "Authenticate with your face via camera." },
                            ] as { id: TwoFaMethod; icon: React.ReactNode; label: string; desc: string }[]).map(({ id, icon, label, desc }) => (
                                <button
                                    key={id}
                                    type="button"
                                    onClick={() => setTwoFaMethod(id)}
                                    className={`w-full flex items-start gap-3 rounded-xl border p-4 text-left transition-all ${
                                        twoFaMethod === id
                                            ? "border-brand-blue-500/50 bg-brand-blue-500/10"
                                            : "border-slate-700 bg-slate-900/50 hover:border-slate-600"
                                    }`}
                                >
                                    <span className="mt-0.5">{icon}</span>
                                    <span>
                                        <span className="block text-sm font-semibold text-slate-100">{label}</span>
                                        <span className="block text-xs text-slate-400 mt-0.5">{desc}</span>
                                    </span>
                                    {twoFaMethod === id && <CheckCircle2 className="size-4 text-brand-blue-400 ml-auto mt-0.5 shrink-0" />}
                                </button>
                            ))}
                        </div>

                        {twoFaMethod === "sms" && (
                            <div className="mb-4">
                                <RBLabel>Phone number</RBLabel>
                                <RBInput
                                    type="tel"
                                    value={phoneNumber}
                                    onChange={(e) => setPhoneNumber(e.target.value)}
                                    placeholder="+1 555 000 0000"
                                />
                            </div>
                        )}

                        <RBButton
                            type="button"
                            className="w-full"
                            disabled={twoFaLoading}
                            onClick={handle2FaSetup}
                        >
                            {twoFaLoading ? <Spinner size="sm" label="Setting up 2FA" /> : null}
                            {twoFaLoading
                                ? "Setting up…"
                                : twoFaMethod === "none"
                                    ? "Skip and go to dashboard"
                                    : twoFaMethod === "face"
                                        ? "Open camera to enroll"
                                        : "Enable and go to dashboard"}
                        </RBButton>

                        {twoFaMethod === "none" && (
                            <p className="text-xs text-slate-500 text-center mt-3">
                                Without 2FA your account is protected by password only.
                            </p>
                        )}
                    </RBCard>
                </div>

                {showFaceModal && (
                    <FaceEnrollModal
                        onClose={() => setShowFaceModal(false)}
                        onEnrolled={() => {
                            setShowFaceModal(false);
                            // Face enrollment successful - go directly to dashboard
                            // No need for additional verification (face already tested during enrollment)
                            router.push("/dashboard");
                            router.refresh();
                        }}
                    />
                )}
            </RBPage>
        );
    }

    return (
        <RBPage className="flex items-center justify-center p-4">
            <div className="relative z-10 w-full max-w-lg">
                <div className="flex items-center justify-center gap-3 mb-8">
                    <Image src="/logo.png" alt="Trady" width={40} height={40} className="h-10 w-10" priority />
                    <span className="text-xl font-bold text-slate-100">Trady</span>
                </div>

                <div className="mb-6">
                    <ProgressIndicator 
                        currentStep={1} 
                        totalSteps={3} 
                        type="numbers" 
                        showLabels 
                        className="justify-center" 
                    />
                </div>

                <RBCard className="p-6 md:p-8">
                    <h2 className="text-2xl font-bold text-slate-100 text-center mb-1">Create your account</h2>
                    <p className="text-sm text-slate-400 text-center mb-6">Quick signup with global ID verification</p>

                    {error && (
                        <Alert variant="error" className="mb-4" onClose={() => setError("")}>
                            {error}
                        </Alert>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="rounded-2xl border border-brand-blue-400/25 bg-gradient-to-br from-brand-blue-500/10 via-slate-950/80 to-brand-green-500/10 p-4 shadow-[0_18px_60px_rgba(6,88,186,0.18)]">
                            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                                <div>
                                    <div className="flex items-center gap-2 text-sm font-semibold text-slate-100">
                                        <Sparkles className="size-4 text-brand-green-300" />
                                        Voice autofill
                                    </div>
                                    <p className="mt-1 text-xs text-slate-400">
                                        Say your profile details in one paragraph. Password stays manual.
                                    </p>
                                </div>
                                <RBButton
                                    type="button"
                                    variant={voiceState === "recording" ? "danger" : "secondary"}
                                    onClick={voiceState === "recording" ? stopVoiceCapture : startVoiceCapture}
                                    disabled={voiceState === "processing"}
                                    className="shrink-0"
                                >
                                    {voiceState === "processing" ? <Spinner size="sm" label="Processing voice" /> : voiceState === "recording" ? <Square className="size-4" /> : <Mic className="size-4" />}
                                    {voiceState === "processing" ? "Reading voice..." : voiceState === "recording" ? "Stop recording" : "Speak profile"}
                                </RBButton>
                            </div>

                            {voiceState === "recording" && (
                                <div className="mt-4 flex h-12 items-center justify-center gap-1 rounded-xl border border-brand-green-400/25 bg-black/25">
                                    {[0, 1, 2, 3, 4, 5, 6].map((bar) => (
                                        <span
                                            key={bar}
                                            className="h-3 w-1 rounded-full bg-brand-green-300 animate-pulse"
                                            style={{ animationDelay: `${bar * 90}ms`, transform: `scaleY(${1 + (bar % 3) * 0.55})` }}
                                        />
                                    ))}
                                </div>
                            )}

                            {voiceError && (
                                <p className="mt-3 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
                                    {voiceError}
                                </p>
                            )}

                            {voiceTranscript && (
                                <div className="mt-4 rounded-xl border border-white/10 bg-slate-950/60 p-3">
                                    <p className="text-[10px] uppercase tracking-widest text-slate-500">Transcript</p>
                                    <p className="mt-1 max-h-24 overflow-y-auto text-xs leading-5 text-slate-300">{voiceTranscript}</p>
                                </div>
                            )}

                            {voiceDraft && (
                                <div className="mt-4 space-y-3">
                                    <div className="flex flex-wrap gap-2">
                                        {[
                                            voiceDraft.name && `Name: ${voiceDraft.name}`,
                                            voiceDraft.email && `Email: ${voiceDraft.email}`,
                                            voiceDraft.phoneNumber && `Phone: ${voiceDraft.phoneNumber}`,
                                            voiceDraft.country && `Country: ${voiceDraft.country}`,
                                            voiceDraft.city && `City: ${voiceDraft.city}`,
                                            voiceDraft.address && `Address: ${voiceDraft.address}`,
                                            voiceDraft.profession && `Profession: ${voiceDraft.profession}`,
                                            voiceDraft.tradingExperience && `Experience: ${voiceDraft.tradingExperience}`,
                                            voiceDraft.preferredMarket && `Market: ${voiceDraft.preferredMarket}`,
                                            voiceDraft.kyc?.fullName && `Legal: ${voiceDraft.kyc.fullName}`,
                                            voiceDraft.kyc?.cinNumber && `ID: ${voiceDraft.kyc.cinNumber}`,
                                            voiceDraft.kyc?.nationality && `Nationality: ${voiceDraft.kyc.nationality}`,
                                            voiceDraft.kyc?.documentCountry && `Doc country: ${voiceDraft.kyc.documentCountry}`,
                                            voiceDraft.kyc?.documentType && `Doc type: ${voiceDraft.kyc.documentType}`,
                                            voiceDraft.kyc?.dateOfBirth && `DOB: ${voiceDraft.kyc.dateOfBirth}`,
                                            voiceDraft.kyc?.expirationDate && `Expires: ${voiceDraft.kyc.expirationDate}`,
                                            voiceDraft.bio && `Bio: ${voiceDraft.bio}`,
                                        ].filter((item): item is string => Boolean(item)).map((item) => (
                                            <span key={item} className="rounded-full border border-brand-blue-400/25 bg-brand-blue-500/10 px-2.5 py-1 text-[11px] font-medium text-brand-blue-100">
                                                {item}
                                            </span>
                                        ))}
                                    </div>
                                    <div className="grid grid-cols-2 gap-2">
                                        <RBButton type="button" onClick={applyVoiceDraft}>
                                            <CheckCircle2 className="size-4" />
                                            Apply autofill
                                        </RBButton>
                                        <RBButton
                                            type="button"
                                            variant="secondary"
                                            onClick={() => {
                                                setVoiceDraft(null);
                                                setVoiceTranscript("");
                                                setVoiceState("idle");
                                            }}
                                        >
                                            Clear
                                        </RBButton>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="rounded-xl border border-slate-800 bg-slate-900/55 p-4">
                            <div className="flex items-center gap-4">
                                <div className="relative flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-brand-blue-400/30 bg-slate-950">
                                    {profilePreview ? (
                                        <Image src={profilePreview} alt="Profile preview" fill className="object-cover" />
                                    ) : (
                                        <UserCircle className="size-10 text-slate-500" />
                                    )}
                                </div>
                                <div className="min-w-0 flex-1">
                                    <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                                        <Upload className="size-4 text-brand-blue-300" />
                                        Profile picture <OptionalMark />
                                    </div>
                                    <p className="mt-1 text-xs text-slate-500">Shown in the dashboard and account menu.</p>
                                    <input
                                        type="file"
                                        accept="image/png,image/jpeg,image/jpg,image/webp"
                                        onChange={(e) => chooseProfilePicture(e.target.files?.[0] || null)}
                                        className="mt-3 block w-full text-xs text-slate-300 file:mr-3 file:rounded-lg file:border file:border-slate-700 file:bg-slate-800 file:px-3 file:py-2 file:text-slate-100"
                                    />
                                </div>
                            </div>
                        </div>

                        <div>
                            <RBLabel>Name <OptionalMark /></RBLabel>
                            <RBInput
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="Your name"
                            />
                        </div>
                        <div>
                            <RBLabel>Email</RBLabel>
                            <RBInput
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                placeholder="trader@example.com"
                            />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                                <RBLabel>Phone number <OptionalMark /></RBLabel>
                                <RBInput
                                    type="tel"
                                    value={phoneNumber}
                                    onChange={(e) => setPhoneNumber(e.target.value)}
                                    placeholder="+216 00 000 000"
                                />
                            </div>
                            <div>
                                <RBLabel>Country <OptionalMark /></RBLabel>
                                <RBInput
                                    value={country}
                                    onChange={(e) => setCountry(e.target.value)}
                                    placeholder="Tunisia"
                                />
                            </div>
                            <div>
                                <RBLabel>City <OptionalMark /></RBLabel>
                                <RBInput
                                    value={city}
                                    onChange={(e) => setCity(e.target.value)}
                                    placeholder="Ariana"
                                />
                            </div>
                            <div>
                                <RBLabel>Profession <OptionalMark /></RBLabel>
                                <RBInput
                                    value={profession}
                                    onChange={(e) => setProfession(e.target.value)}
                                    placeholder="Student, trader, analyst..."
                                />
                            </div>
                        </div>
                        <div>
                            <RBLabel>Address <OptionalMark /></RBLabel>
                            <RBInput
                                value={address}
                                onChange={(e) => setAddress(e.target.value)}
                                placeholder="Street, city, postal code"
                            />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                                <RBLabel>Trading experience <OptionalMark /></RBLabel>
                                <RBInput
                                    value={tradingExperience}
                                    onChange={(e) => setTradingExperience(e.target.value)}
                                    placeholder="Beginner, intermediate, 2 years..."
                                />
                            </div>
                            <div>
                                <RBLabel>Preferred market <OptionalMark /></RBLabel>
                                <RBInput
                                    value={preferredMarket}
                                    onChange={(e) => setPreferredMarket(e.target.value)}
                                    placeholder="Forex, crypto, stocks..."
                                />
                            </div>
                        </div>
                        <div>
                            <RBLabel>Short profile <OptionalMark /></RBLabel>
                            <textarea
                                value={bio}
                                onChange={(e) => setBio(e.target.value)}
                                rows={3}
                                placeholder="Tell us your trading goals and learning focus."
                                className="min-h-24 w-full rounded-xl border border-slate-700 bg-slate-900/70 px-3 py-2 text-sm text-slate-100 outline-none transition-colors placeholder:text-slate-500 focus:border-brand-blue-500 focus:ring-2 focus:ring-brand-blue-500/20"
                            />
                        </div>
                        <div>
                            <RBLabel>Password</RBLabel>
                            <div className="relative">
                                <RBInput
                                    type={showPw ? "text" : "password"}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    className="pr-11"
                                    placeholder="Min 6 characters"
                                    autoComplete="new-password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPw(!showPw)}
                                    aria-label={showPw ? "Hide password" : "Show password"}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors rounded p-0.5"
                                >
                                    {showPw ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                                </button>
                            </div>
                            {/* Password strength indicator */}
                            {password.length > 0 && (
                                <div className="mt-2 space-y-1">
                                    <div className="flex gap-1">
                                        {[1, 2, 3, 4].map((level) => (
                                            <span
                                                key={level}
                                                className={`h-1 flex-1 rounded-full transition-colors ${
                                                    password.length >= level * 3
                                                        ? level <= 1 ? "bg-rose-500"
                                                          : level <= 2 ? "bg-amber-500"
                                                          : level <= 3 ? "bg-brand-blue-500"
                                                          : "bg-brand-green-500"
                                                        : "bg-white/10"
                                                }`}
                                            />
                                        ))}
                                    </div>
                                    <p className="text-[10px] text-slate-500">
                                        {password.length < 6 ? "Too short (min 6 chars)" : password.length < 9 ? "Acceptable" : password.length < 12 ? "Good" : "Strong"}
                                    </p>
                                </div>
                            )}
                        </div>

                        <div className="rounded-xl border border-slate-800 bg-slate-900/55 p-4 space-y-3">
                            <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                                <ShieldCheck className="size-4 text-brand-blue-400" /> Identity verification <OptionalMark />
                            </div>

                            <div>
                                <RBLabel>ID card image <OptionalMark /></RBLabel>
                                <input
                                    type="file"
                                    accept="image/png,image/jpeg,image/jpg,image/webp,image/heic,image/heif"
                                    onChange={(e) => setIdCardFile(e.target.files?.[0] || null)}
                                    className="block w-full text-xs text-slate-300 file:mr-3 file:rounded-lg file:border file:border-slate-700 file:bg-slate-800 file:px-3 file:py-2 file:text-slate-100"
                                />
                            </div>

                            <RBButton type="button" variant="secondary" className="w-full" onClick={runOcr} disabled={ocrLoading || !idCardFile}>
                                {ocrLoading ? <Spinner size="sm" label="Scanning" /> : <ScanText className="size-4" />}
                                {ocrLoading ? "Scanning…" : "Scan and extract"}
                            </RBButton>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                <div>
                                    <RBLabel className="text-xs">Extracted full name <OptionalMark /></RBLabel>
                                    <RBInput value={kycData.fullName} onChange={(e) => setKycData((prev) => ({ ...prev, fullName: e.target.value }))} />
                                </div>
                                <div>
                                    <RBLabel className="text-xs">Document number <OptionalMark /></RBLabel>
                                    <RBInput value={kycData.cinNumber} onChange={(e) => setKycData((prev) => ({ ...prev, cinNumber: e.target.value }))} />
                                </div>
                                <div>
                                    <RBLabel className="text-xs">Nationality <OptionalMark /></RBLabel>
                                    <RBInput value={kycData.nationality} onChange={(e) => setKycData((prev) => ({ ...prev, nationality: e.target.value }))} />
                                </div>
                                <div>
                                    <RBLabel className="text-xs">Document country <OptionalMark /></RBLabel>
                                    <RBInput value={kycData.documentCountry} onChange={(e) => setKycData((prev) => ({ ...prev, documentCountry: e.target.value }))} />
                                </div>
                                <div>
                                    <RBLabel className="text-xs">Document type <OptionalMark /></RBLabel>
                                    <RBInput value={kycData.documentType} onChange={(e) => setKycData((prev) => ({ ...prev, documentType: e.target.value }))} />
                                </div>
                                <div>
                                    <RBLabel className="text-xs">Date of birth <OptionalMark /></RBLabel>
                                    <RBInput value={kycData.dateOfBirth} onChange={(e) => setKycData((prev) => ({ ...prev, dateOfBirth: e.target.value }))} />
                                </div>
                                <div>
                                    <RBLabel className="text-xs">Expiration date <OptionalMark /></RBLabel>
                                    <RBInput value={kycData.expirationDate} onChange={(e) => setKycData((prev) => ({ ...prev, expirationDate: e.target.value }))} />
                                </div>
                            </div>

                            {/* OCR confidence indicator */}
                            <div className="rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-2.5 space-y-1.5">
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-slate-400">Scan confidence</span>
                                    <span className={`font-bold ${
                                        kycData.confidenceBasic >= 0.6 ? "text-brand-green-400"
                                        : kycData.confidenceBasic >= 0.35 ? "text-amber-400"
                                        : kycData.confidenceBasic > 0 ? "text-rose-400"
                                        : "text-slate-500"
                                    }`}>
                                        {Math.round(kycData.confidenceBasic * 100)}%
                                        {kycData.confidenceBasic >= 0.6 ? " ✓ Acceptable" : kycData.confidenceBasic >= 0.35 ? " — Review fields" : kycData.confidenceBasic > 0 ? " ✗ Too low" : ""}
                                    </span>
                                </div>
                                <div className="h-1 rounded-full bg-white/10 overflow-hidden">
                                    <div
                                        className={`h-full rounded-full transition-all duration-500 ${
                                            kycData.confidenceBasic >= 0.6 ? "bg-brand-green-500"
                                            : kycData.confidenceBasic >= 0.35 ? "bg-amber-500"
                                            : "bg-rose-500"
                                        }`}
                                        style={{ width: `${Math.round(kycData.confidenceBasic * 100)}%` }}
                                    />
                                </div>
                                {kycData.confidenceBasic > 0 && kycData.confidenceBasic < 0.35 && (
                                    <p className="text-[10px] text-amber-400/80">Low scan quality. Review the fields manually before continuing.</p>
                                )}
                            </div>

                            <label className="flex items-start gap-2 text-xs text-slate-400">
                                <input
                                    type="checkbox"
                                    checked={kycConfirmed}
                                    onChange={(e) => setKycConfirmed(e.target.checked)}
                                    className="mt-0.5"
                                />
                                I confirm that the extracted identity data is correct.
                            </label>
                        </div>

                        <RBButton
                            type="submit"
                            disabled={loading}
                            className="w-full"
                        >
                            {loading ? <Spinner size="sm" label="Creating account" /> : null}
                            {loading ? "Creating account…" : "Create account"}
                        </RBButton>
                    </form>

                    <div className="mt-5">
                        <SocialAuthButtons mode="register" />
                    </div>

                    <div className="mt-6 space-y-2">
                        {["Multi-agent AI signals", "Real-time market news", "Global ID verification"].map((f) => (
                            <div key={f} className="flex items-center gap-2 text-xs text-slate-400">
                                <CheckCircle2 className="size-3.5 text-green-400" />
                                {f}
                            </div>
                        ))}
                    </div>

                    <p className="text-sm text-slate-400 text-center mt-6">
                        Already have an account?{" "}
                        <Link href="/login" className="text-brand-green-400 hover:text-brand-green-300 font-medium transition-colors">
                            Sign in
                        </Link>
                    </p>
                </RBCard>
            </div>
        </RBPage>
    );
}



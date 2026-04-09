"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { Eye, EyeOff, CheckCircle2, ScanText, ShieldCheck, Mail, Smartphone, Scan, ArrowRight, Shield } from "lucide-react";
import { RBButton, RBCard, RBInput, RBLabel, RBPage } from "@/components/reactbits";
import { ProgressIndicator } from "@/components/ui/progress-indicator";
import { Alert } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import FaceEnrollModal from "@/components/FaceEnrollModal";
import TwoFASetupVerification from "@/components/TwoFASetupVerification";

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

export default function RegisterPage() {
    const router = useRouter();
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
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
                setError(data.error || data.quality?.note || "OCR scan failed");
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
            setError("Unable to run OCR right now.");
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

        if (!kycConfirmed) {
            setError("Confirm the extracted identity data before creating your account.");
            setLoading(false);
            return;
        }

        const res = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name,
                email,
                password,
                kyc: {
                    confirmed: true,
                    fullName: kycData.fullName,
                    cinNumber: kycData.cinNumber,
                    nationality: kycData.nationality,
                    documentCountry: kycData.documentCountry,
                    documentType: kycData.documentType,
                    dateOfBirth: kycData.dateOfBirth,
                    expirationDate: kycData.expirationDate,
                    confidenceBasic: kycData.confidenceBasic,
                    ocrText: kycData.ocrText,
                },
            }),
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
                        <p className="text-sm text-slate-400 text-center mb-6">Choose a two-factor authentication method. You can change this later in settings.</p>

                        {twoFaError && (
                            <Alert variant="error" className="mb-4" onClose={() => setTwoFaError("")}>
                                {twoFaError}
                            </Alert>
                        )}

                        <div className="space-y-3 mb-6">
                            {([
                                { id: "none",  icon: <ArrowRight className="size-5 text-slate-400" />, label: "Skip for now",   desc: "You can enable 2FA later in settings." },
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
                        <div>
                            <RBLabel>Name</RBLabel>
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
                                <ShieldCheck className="size-4 text-brand-blue-400" /> Identity verification (Gemini)
                            </div>

                            <div>
                                <RBLabel>ID card image</RBLabel>
                                <input
                                    type="file"
                                    accept="image/png,image/jpeg,image/jpg"
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
                                    <RBLabel className="text-xs">Extracted full name</RBLabel>
                                    <RBInput value={kycData.fullName} onChange={(e) => setKycData((prev) => ({ ...prev, fullName: e.target.value }))} />
                                </div>
                                <div>
                                    <RBLabel className="text-xs">Document number</RBLabel>
                                    <RBInput value={kycData.cinNumber} onChange={(e) => setKycData((prev) => ({ ...prev, cinNumber: e.target.value }))} />
                                </div>
                                <div>
                                    <RBLabel className="text-xs">Nationality</RBLabel>
                                    <RBInput value={kycData.nationality} onChange={(e) => setKycData((prev) => ({ ...prev, nationality: e.target.value }))} />
                                </div>
                                <div>
                                    <RBLabel className="text-xs">Document country</RBLabel>
                                    <RBInput value={kycData.documentCountry} onChange={(e) => setKycData((prev) => ({ ...prev, documentCountry: e.target.value }))} />
                                </div>
                                <div>
                                    <RBLabel className="text-xs">Document type</RBLabel>
                                    <RBInput value={kycData.documentType} onChange={(e) => setKycData((prev) => ({ ...prev, documentType: e.target.value }))} />
                                </div>
                                <div>
                                    <RBLabel className="text-xs">Date of birth</RBLabel>
                                    <RBInput value={kycData.dateOfBirth} onChange={(e) => setKycData((prev) => ({ ...prev, dateOfBirth: e.target.value }))} />
                                </div>
                                <div>
                                    <RBLabel className="text-xs">Expiration date</RBLabel>
                                    <RBInput value={kycData.expirationDate} onChange={(e) => setKycData((prev) => ({ ...prev, expirationDate: e.target.value }))} />
                                </div>
                            </div>

                            {/* OCR confidence indicator */}
                            <div className="rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-2.5 space-y-1.5">
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-slate-400">Scan confidence</span>
                                    <span className={`font-bold ${
                                        kycData.confidenceBasic >= 0.8 ? "text-brand-green-400"
                                        : kycData.confidenceBasic >= 0.5 ? "text-amber-400"
                                        : kycData.confidenceBasic > 0 ? "text-rose-400"
                                        : "text-slate-500"
                                    }`}>
                                        {Math.round(kycData.confidenceBasic * 100)}%
                                        {kycData.confidenceBasic >= 0.8 ? " ✓ Acceptable" : kycData.confidenceBasic >= 0.5 ? " — Low" : kycData.confidenceBasic > 0 ? " ✗ Too low" : ""}
                                    </span>
                                </div>
                                <div className="h-1 rounded-full bg-white/10 overflow-hidden">
                                    <div
                                        className={`h-full rounded-full transition-all duration-500 ${
                                            kycData.confidenceBasic >= 0.8 ? "bg-brand-green-500"
                                            : kycData.confidenceBasic >= 0.5 ? "bg-amber-500"
                                            : "bg-rose-500"
                                        }`}
                                        style={{ width: `${Math.round(kycData.confidenceBasic * 100)}%` }}
                                    />
                                </div>
                                {kycData.confidenceBasic > 0 && kycData.confidenceBasic < 0.8 && (
                                    <p className="text-[10px] text-amber-400/80">Minimum required: 80%. Try uploading a clearer image.</p>
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

                    <div className="mt-6 space-y-2">
                        {["Multi-agent AI signals", "Real-time analytics", "Global ID verification"].map((f) => (
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



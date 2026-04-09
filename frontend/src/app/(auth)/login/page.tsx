"use client";

import { useState, useId } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { Eye, EyeOff } from "lucide-react";
import { RBButton, RBCard, RBInput, RBLabel, RBPage } from "@/components/reactbits";
import { Alert } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import OtpStep from "@/components/OtpStep";
import FaceVerifyStep from "@/components/FaceVerifyStep";

type Step = "credentials" | "otp" | "face";

/* very light email format check — no blocking real validation here */
const isValidEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);

export default function LoginPage() {
    const router = useRouter();
    const emailId = useId();
    const passwordId = useId();
    const emailErrId = useId();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPw, setShowPw] = useState(false);
    const [rememberMe, setRememberMe] = useState(false);
    const [error, setError] = useState("");
    const [emailTouched, setEmailTouched] = useState(false);
    const [loading, setLoading] = useState(false);
    const [step, setStep] = useState<Step>("credentials");
    const [twoFaMethod, setTwoFaMethod] = useState<"email" | "sms" | "face">("email");

    const emailError = emailTouched && email && !isValidEmail(email)
        ? "Enter a valid email address."
        : null;

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setEmailTouched(true);
        if (emailError) return;

        setError("");
        setLoading(true);

        // ── Step 1: Check Django backend for 2FA requirements ─────────────
        try {
            const djangoRes = await fetch("/api/django-auth/login", {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: email, password }),
            });
            const djangoData = await djangoRes.json();

            if (djangoData.requires_2fa) {
                const method = djangoData.method as "email" | "sms" | "face";
                setTwoFaMethod(method);
                setStep(method === "face" ? "face" : "otp");
                setLoading(false);
                return;
            }
        } catch {
            // Django may be offline; proceed with NextAuth only
        }

        // ── Step 2: Establish NextAuth session ────────────────────────────
        const res = await signIn("credentials", {
            email,
            password,
            redirect: false,
        });

        setLoading(false);

        if (res?.error) {
            setError("Invalid email or password. Please try again.");
        } else {
            // Ensure Django user exists (re-sync in case django-register was missed at registration).
            // This is a no-op if the user already exists — DjangoRegisterView does get_or_create.
            try {
                await fetch("/api/django-auth/django-register", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email, password }),
                });
            } catch {
                // Non-blocking — Django offline means 2FA unavailable but login still works
            }
            router.push("/dashboard");
            router.refresh();
        }
    }

    async function handleTwoFaSuccess() {
        // 2FA passed — now establish NextAuth session
        setLoading(true);
        const res = await signIn("credentials", {
            email,
            password,
            redirect: false,
        });
        setLoading(false);
        if (res?.error) {
            setError("Session could not be established. Please sign in again.");
            setStep("credentials");
        } else {
            router.push("/dashboard");
            router.refresh();
        }
    }

    function handleFallback() {
        // Switch to OTP if face fails, or back to credentials
        if (step === "face") {
            setTwoFaMethod("email");
            setStep("otp");
        } else {
            setStep("credentials");
        }
    }

    return (
        <RBPage className="flex items-center justify-center p-4">
            <div className="relative z-10 w-full max-w-md animate-fade-in">
                <div className="flex items-center justify-center gap-3 mb-8">
                    <Image src="/logo.png" alt="Trady" width={40} height={40} className="h-10 w-10" priority />
                    <span className="text-xl font-bold text-slate-100">Trady</span>
                </div>

                <RBCard className="p-8">
                    {/* ── OTP step ───────────────────────────────────────────────────── */}
                    {step === "otp" && (
                        <OtpStep
                            method={twoFaMethod as "email" | "sms"}
                            onSuccess={handleTwoFaSuccess}
                            onFallback={handleFallback}
                        />
                    )}

                    {/* ── Face step ──────────────────────────────────────────────────── */}
                    {step === "face" && (
                        <FaceVerifyStep
                            onSuccess={handleTwoFaSuccess}
                            onFallback={handleFallback}
                        />
                    )}

                    {/* ── Credentials step ───────────────────────────────────────────── */}
                    {step === "credentials" && (
                        <>
                            <h2 className="text-2xl font-bold text-slate-100 text-center mb-1">Welcome back</h2>
                            <p className="text-sm text-slate-400 text-center mb-6">Sign in to the trading dashboard</p>

                            {error && (
                                <Alert variant="error" className="mb-4" onClose={() => setError("")}>
                                    {error}
                                </Alert>
                            )}

                            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
                                {/* Email */}
                                <div>
                                    <RBLabel htmlFor={emailId}>Email</RBLabel>
                                    <RBInput
                                        id={emailId}
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        onBlur={() => setEmailTouched(true)}
                                        required
                                        placeholder="trader@example.com"
                                        aria-describedby={emailError ? emailErrId : undefined}
                                        aria-invalid={!!emailError}
                                        autoComplete="email"
                                        className={emailError ? "border-rose-500/60 focus:ring-rose-500/35" : ""}
                                    />
                                    {emailError && (
                                        <p id={emailErrId} className="mt-1 text-xs text-rose-400" role="alert">
                                            {emailError}
                                        </p>
                                    )}
                                </div>

                                {/* Password */}
                                <div>
                                    <div className="flex items-center justify-between mb-1.5">
                                        <RBLabel htmlFor={passwordId} className="mb-0">Password</RBLabel>
                                    </div>
                                    <div className="relative">
                                        <RBInput
                                            id={passwordId}
                                            type={showPw ? "text" : "password"}
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            required
                                            className="pr-11"
                                            placeholder="••••••••"
                                            autoComplete="current-password"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowPw(!showPw)}
                                            aria-label={showPw ? "Hide password" : "Show password"}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors rounded p-0.5 focus-visible:ring-2 focus-visible:ring-brand-blue-500/40 focus-visible:outline-none"
                                        >
                                            {showPw ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                                        </button>
                                    </div>
                                </div>

                                {/* Remember me */}
                                <label className="flex items-center gap-2 cursor-pointer select-none group">
                                    <input
                                        type="checkbox"
                                        checked={rememberMe}
                                        onChange={(e) => setRememberMe(e.target.checked)}
                                        className="size-4 rounded border-slate-700 bg-slate-900/70 text-brand-blue-600 focus:ring-brand-blue-500/40 focus:ring-offset-0 cursor-pointer"
                                    />
                                    <span className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors">
                                        Remember me
                                    </span>
                                </label>

                                <RBButton
                                    type="submit"
                                    disabled={loading}
                                    className="w-full mt-2"
                                >
                                    {loading ? (
                                        <>
                                            <Spinner size="sm" label="Signing in" />
                                            Signing in…
                                        </>
                                    ) : (
                                        "Sign in"
                                    )}
                                </RBButton>
                            </form>

                            <p className="text-sm text-slate-400 text-center mt-6">
                                Don&apos;t have an account?{" "}
                                <Link
                                    href="/register"
                                    className="text-brand-green-400 hover:text-brand-green-300 font-medium transition-colors"
                                >
                                    Create one
                                </Link>
                            </p>
                        </>
                    )}
                </RBCard>
            </div>
        </RBPage>
    );
}



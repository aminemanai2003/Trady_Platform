"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { Loader2, Eye, EyeOff } from "lucide-react";
import { RBButton, RBCard, RBInput, RBLabel, RBPage } from "@/components/reactbits";
import OtpStep from "@/components/OtpStep";
import FaceVerifyStep from "@/components/FaceVerifyStep";

type Step = "credentials" | "otp" | "face";

export default function LoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPw, setShowPw] = useState(false);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [step, setStep] = useState<Step>("credentials");
    const [twoFaMethod, setTwoFaMethod] = useState<"email" | "sms" | "face">("email");

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        setLoading(true);

        // ── Step 1: Check Django backend for 2FA requirements ─────────────
        try {
            const djangoRes = await fetch("/api/django-auth/login", {
                method: "POST",
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
            setError(res.error);
        } else {
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
            setError(res.error);
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
            <div className="relative z-10 w-full max-w-md">
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
                                <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-sm text-rose-400 text-center">
                                    {error}
                                </div>
                            )}

                            <form onSubmit={handleSubmit} className="space-y-4">
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
                                            placeholder="********"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowPw(!showPw)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                                        >
                                            {showPw ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                                        </button>
                                    </div>
                                </div>

                                <RBButton
                                    type="submit"
                                    disabled={loading}
                                    className="w-full"
                                >
                                    {loading ? <Loader2 className="size-4 animate-spin" /> : null}
                                    {loading ? "Signing in..." : "Sign in"}
                                </RBButton>
                            </form>

                            <p className="text-sm text-slate-400 text-center mt-6">
                                Don&apos;t have an account?{" "}
                                <Link href="/register" className="text-green-400 hover:text-[#4D8048] font-medium transition-colors">
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



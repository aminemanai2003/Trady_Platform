"use client";

import { useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { RBButton } from "@/components/reactbits";

interface OtpStepProps {
    method: "email" | "sms";
    onSuccess: () => void;
    onFallback: () => void;
}

export default function OtpStep({ method, onSuccess, onFallback }: OtpStepProps) {
    const [digits, setDigits] = useState(["", "", "", "", "", ""]);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [resending, setResending] = useState(false);
    const inputs = useRef<(HTMLInputElement | null)[]>([]);

    function handleChange(idx: number, val: string) {
        if (!/^\d?$/.test(val)) return;
        const next = [...digits];
        next[idx] = val;
        setDigits(next);
        if (val && idx < 5) inputs.current[idx + 1]?.focus();
    }

    function handleKeyDown(idx: number, e: React.KeyboardEvent<HTMLInputElement>) {
        if (e.key === "Backspace" && !digits[idx] && idx > 0) {
            inputs.current[idx - 1]?.focus();
        }
    }

    function handlePaste(e: React.ClipboardEvent<HTMLInputElement>) {
        const text = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
        if (text.length === 6) {
            setDigits(text.split(""));
            inputs.current[5]?.focus();
        }
    }

    async function handleVerify() {
        const otp = digits.join("");
        if (otp.length < 6) { setError("Enter all 6 digits."); return; }
        setError("");
        setLoading(true);
        try {
            const res = await fetch("/api/django-auth/verify-otp", {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ otp }),
            });
            const data = await res.json();
            if (data.success) {
                onSuccess();
            } else {
                setError(data.message ?? "Invalid code.");
                setDigits(["", "", "", "", "", ""]);
                inputs.current[0]?.focus();
            }
        } catch {
            setError("Network error. Please try again.");
        } finally {
            setLoading(false);
        }
    }

    async function handleResend() {
        setResending(true);
        setError("");
        try {
            await fetch("/api/django-auth/send-otp", {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ method }),
            });
        } finally {
            setResending(false);
        }
    }

    return (
        <div className="space-y-6">
            <div className="text-center">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-sky-600/20 mb-3">
                    <span className="text-2xl">{method === "sms" ? "📱" : "✉️"}</span>
                </div>
                <h3 className="text-lg font-semibold text-slate-100">Verification code</h3>
                <p className="text-sm text-slate-400 mt-1">
                    A 6-digit code was sent to your {method === "sms" ? "phone" : "email"}.
                </p>
            </div>

            {/* OTP digit inputs */}
            <div className="flex justify-center gap-2">
                {digits.map((d, i) => (
                    <input
                        key={i}
                        ref={(el) => { inputs.current[i] = el; }}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        value={d}
                        onChange={(e) => handleChange(i, e.target.value)}
                        onKeyDown={(e) => handleKeyDown(i, e)}
                        onPaste={handlePaste}
                        className={
                            "w-11 h-13 text-center text-xl font-bold rounded-xl border " +
                            "bg-slate-800 text-slate-100 focus:outline-none focus:ring-2 " +
                            (error
                                ? "border-rose-500/60 focus:ring-rose-500/40"
                                : "border-slate-700 focus:ring-sky-500/40")
                        }
                    />
                ))}
            </div>

            {error && (
                <p className="text-sm text-rose-400 text-center">{error}</p>
            )}

            <RBButton
                className="w-full"
                disabled={loading || digits.join("").length < 6}
                onClick={handleVerify}
            >
                {loading ? <Loader2 className="size-4 animate-spin" /> : null}
                {loading ? "Verifying…" : "Verify code"}
            </RBButton>

            <div className="flex items-center justify-between text-sm">
                <button
                    type="button"
                    onClick={handleFallback}
                    className="text-slate-500 hover:text-slate-300 transition-colors"
                >
                    Use a different method
                </button>
                <button
                    type="button"
                    onClick={handleResend}
                    disabled={resending}
                    className="text-sky-400 hover:text-sky-300 transition-colors disabled:opacity-50"
                >
                    {resending ? "Resending…" : "Resend code"}
                </button>
            </div>
        </div>
    );

    function handleFallback() { onFallback(); }
}

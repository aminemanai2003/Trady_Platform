"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, CheckCircle2, Loader2, X, XCircle, Mail, Smartphone } from "lucide-react";
import { RBButton } from "@/components/reactbits";

type TwoFaMethod = "face" | "email" | "sms";
type Phase = "init" | "idle" | "sending_otp" | "otp_sent" | "verifying" | "success" | "failed" | "error";

interface TwoFASetupVerificationProps {
    method: TwoFaMethod;
    phoneNumber?: string;
    onComplete: () => void;
    onSkip: () => void;
}

function captureBase64(video: HTMLVideoElement): string {
    const canvas = document.createElement("canvas");
    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")!.drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.85).split(",")[1];
}

export default function TwoFASetupVerification({
    method,
    phoneNumber,
    onComplete,
    onSkip,
}: TwoFASetupVerificationProps) {
    const [phase, setPhase] = useState<Phase>("init");
    const [detail, setDetail] = useState("");
    const [digits, setDigits] = useState(["", "", "", "", "", ""]);
    const [error, setError] = useState("");
    const inputs = useRef<(HTMLInputElement | null)[]>([]);
    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);

    // ── Face verification: Initialize camera ──────────────────────────────────
    useEffect(() => {
        if (method !== "face") return;
        let cancelled = false;
        navigator.mediaDevices
            .getUserMedia({ video: { facingMode: "user", width: 640, height: 480 }, audio: false })
            .then((stream) => {
                if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return; }
                streamRef.current = stream;
                if (videoRef.current) videoRef.current.srcObject = stream;
                setPhase("idle");
            })
            .catch(() => setPhase("error"));
        return () => {
            cancelled = true;
            streamRef.current?.getTracks().forEach((t) => t.stop());
        };
    }, [method]);

    // ── OTP verification: Send OTP on mount ────────────────────────────────────
    useEffect(() => {
        if (method === "email" || method === "sms") {
            sendOTP();
        }
    }, [method]);

    async function sendOTP() {
        setPhase("sending_otp");
        setError("");
        try {
            const res = await fetch("/api/django-auth/send-otp", {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ method }),
            });
            const data = await res.json();
            if (res.ok || data.success) {
                setPhase("otp_sent");
            } else {
                setError(data.message ?? "Failed to send OTP.");
                setPhase("failed");
            }
        } catch {
            setError("Network error while sending OTP.");
            setPhase("failed");
        }
    }

    // ── Face capture & verify ──────────────────────────────────────────────────
    const captureFace = useCallback(async () => {
        if (!videoRef.current) return;
        const b64 = captureBase64(videoRef.current);
        setPhase("verifying");
        setDetail("");

        // 120-second timeout — the AI model may need to download on first use
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120_000);

        try {
            const res = await fetch("/api/django-auth/verify-2fa-setup", {
                method: "POST",
                signal: controller.signal,
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ method: "face", image: b64 }),
            });
            clearTimeout(timeoutId);
            const data = await res.json();
            if (data.success && data.verified) {
                setPhase("success");
                streamRef.current?.getTracks().forEach((t) => t.stop());
                setTimeout(onComplete, 1200);
            } else {
                setDetail(data.detail ?? data.message ?? "Face verification failed.");
                setPhase("failed");
            }
        } catch (err: unknown) {
            clearTimeout(timeoutId);
            if (err instanceof Error && err.name === "AbortError") {
                setDetail("The AI model is still loading. Please wait 30 seconds and try again.");
            } else if (err instanceof Error) {
                console.error("Face verification error:", err);
                setDetail(`Network error: ${err.message}. Check that Django is running on port 8000.`);
            } else {
                console.error("Unknown error during face verification:", err);
                setDetail("Network error during verification. Make sure the backend is running.");
            }
            setPhase("failed");
        }
    }, [onComplete]);

    // ── OTP input handlers ─────────────────────────────────────────────────────
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

    // ── OTP verify ─────────────────────────────────────────────────────────────
    async function verifyOTP() {
        const otp = digits.join("");
        if (otp.length < 6) { setError("Enter all 6 digits."); return; }
        setError("");
        setPhase("verifying");
        try {
            const res = await fetch("/api/django-auth/verify-2fa-setup", {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ method, otp }),
            });
            const data = await res.json();
            if (data.success && data.verified) {
                setPhase("success");
                setTimeout(onComplete, 1200);
            } else {
                setError(data.message ?? "Invalid code.");
                setDigits(["", "", "", "", "", ""]);
                inputs.current[0]?.focus();
                setPhase("otp_sent");
            }
        } catch {
            setError("Network error. Please try again.");
            setPhase("otp_sent");
        }
    }

    // ── Render Face Verification UI ───────────────────────────────────────────
    if (method === "face") {
        return (
            <div className="space-y-5">
                <div className="text-center">
                    <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-sky-600/20 mb-3">
                        <Camera className="size-7 text-sky-400" />
                    </div>
                    <h3 className="text-2xl font-bold text-slate-100">Verify face setup</h3>
                    <p className="text-sm text-slate-400 mt-2">
                        Capture your face to confirm Face ID is working correctly.
                    </p>
                </div>

                {/* Camera preview */}
                <div className="relative mx-auto w-full aspect-[4/3] rounded-2xl overflow-hidden bg-slate-950 border border-slate-700">
                    <video
                        ref={videoRef}
                        autoPlay
                        playsInline
                        muted
                        className="w-full h-full object-cover scale-x-[-1]"
                    />

                    {/* Face guide oval */}
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <div className="w-40 h-48 rounded-full border-2 border-sky-400/60 opacity-60" />
                    </div>

                    {phase === "init" && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/80">
                            <Loader2 className="size-7 text-sky-400 animate-spin mb-2" />
                            <span className="text-sm text-slate-300">Starting camera…</span>
                        </div>
                    )}
                    {phase === "error" && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/90 px-4">
                            <XCircle className="size-7 text-rose-400 mb-2" />
                            <span className="text-sm text-slate-300 text-center">
                                Camera access denied. Allow camera in browser settings.
                            </span>
                        </div>
                    )}
                    {phase === "verifying" && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/80 px-4">
                            <Loader2 className="size-7 text-sky-400 animate-spin mb-2" />
                            <span className="text-sm text-slate-300 text-center">Verifying your face…</span>
                            <span className="text-xs text-slate-500 text-center mt-1">This may take up to 30s on first use</span>
                        </div>
                    )}
                    {phase === "success" && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-emerald-900/80">
                            <CheckCircle2 className="size-9 text-emerald-400 mb-2" />
                            <span className="text-sm font-semibold text-emerald-200">Face verified!</span>
                        </div>
                    )}
                </div>

                {phase === "failed" && detail && (
                    <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-sm text-rose-400 text-center">
                        {detail}
                    </div>
                )}

                <div className="space-y-3">
                    {phase === "idle" && (
                        <RBButton className="w-full" onClick={captureFace}>
                            <Camera className="size-4" />
                            Capture &amp; verify
                        </RBButton>
                    )}
                    {phase === "failed" && (
                        <RBButton className="w-full" onClick={() => { setDetail(""); setPhase("idle"); }}>
                            Try again
                        </RBButton>
                    )}
                    {(phase === "verifying" || phase === "init") && (
                        <RBButton className="w-full" disabled>
                            <Loader2 className="size-4 animate-spin" />
                            Please wait…
                        </RBButton>
                    )}
                    <RBButton variant="secondary" className="w-full" onClick={onSkip}>
                        Skip for now
                    </RBButton>
                </div>
            </div>
        );
    }

    // ── Render OTP Verification UI ────────────────────────────────────────────
    return (
        <div className="space-y-6">
            <div className="text-center">
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-sky-600/20 mb-3">
                    {method === "sms" ? <Smartphone className="size-7 text-sky-400" /> : <Mail className="size-7 text-sky-400" />}
                </div>
                <h3 className="text-2xl font-bold text-slate-100">Verify {method.toUpperCase()} setup</h3>
                <p className="text-sm text-slate-400 mt-2">
                    {phase === "sending_otp" && "Sending verification code…"}
                    {phase === "otp_sent" && `A 6-digit code was sent to your ${method === "sms" ? "phone" : "email"}.`}
                    {phase === "failed" && "Failed to send code."}
                    {phase === "success" && "Code verified successfully!"}
                </p>
            </div>

            {phase === "sending_otp" && (
                <div className="flex justify-center py-8">
                    <Loader2 className="size-8 text-sky-400 animate-spin" />
                </div>
            )}

            {(phase === "otp_sent" || phase === "verifying") && (
                <>
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
                                disabled={phase === "verifying"}
                            />
                        ))}
                    </div>

                    {error && (
                        <p className="text-sm text-rose-400 text-center">{error}</p>
                    )}

                    <RBButton
                        className="w-full"
                        disabled={phase === "verifying" || digits.join("").length < 6}
                        onClick={verifyOTP}
                    >
                        {phase === "verifying" ? <Loader2 className="size-4 animate-spin" /> : null}
                        {phase === "verifying" ? "Verifying…" : "Verify code"}
                    </RBButton>

                    <div className="flex items-center justify-between text-sm">
                        <button
                            type="button"
                            onClick={onSkip}
                            className="text-slate-500 hover:text-slate-300 transition-colors"
                        >
                            Skip for now
                        </button>
                        <button
                            type="button"
                            onClick={sendOTP}
                            className="text-sky-400 hover:text-sky-300 transition-colors"
                        >
                            Resend code
                        </button>
                    </div>
                </>
            )}

            {phase === "failed" && (
                <div className="space-y-3">
                    <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-sm text-rose-400 text-center">
                        {error || "Failed to send verification code."}
                    </div>
                    <RBButton className="w-full" onClick={sendOTP}>
                        Try again
                    </RBButton>
                    <RBButton variant="secondary" className="w-full" onClick={onSkip}>
                        Skip for now
                    </RBButton>
                </div>
            )}

            {phase === "success" && (
                <div className="flex flex-col items-center py-8">
                    <CheckCircle2 className="size-12 text-emerald-400 mb-3" />
                    <span className="text-lg font-semibold text-emerald-200">Verification successful!</span>
                </div>
            )}
        </div>
    );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, CheckCircle2, Loader2, ScanFace, XCircle } from "lucide-react";
import { RBButton } from "@/components/reactbits";

type Phase =
    | "init"        // requesting camera permission
    | "countdown"   // 3-2-1 countdown before capture
    | "verifying"   // API call in progress
    | "success"
    | "failed"
    | "error";      // camera access failed

interface FaceVerifyStepProps {
    onSuccess:  () => void;
    onFallback: () => void;
}

function captureBase64(video: HTMLVideoElement): string {
    const canvas = document.createElement("canvas");
    canvas.width  = video.videoWidth  || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext("2d")!.drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.92).split(",")[1];
}

export default function FaceVerifyStep({ onSuccess, onFallback }: FaceVerifyStepProps) {
    const videoRef   = useRef<HTMLVideoElement>(null);
    const streamRef  = useRef<MediaStream | null>(null);

    const [phase,      setPhase]      = useState<Phase>("init");
    const [countdown,  setCountdown]  = useState(3);
    const [detail,     setDetail]     = useState("");
    const [confidence, setConfidence] = useState(0);
    const [flash,      setFlash]      = useState(false);
    // Bumping this key restarts the camera effect cleanly
    // and correctly handles React Strict Mode's double-invoke.
    const [cameraKey, setCameraKey]   = useState(0);

    // ── Camera start — re-runs every time cameraKey changes ──────────────────
    useEffect(() => {
        let cancelled = false;

        setPhase("init");
        setDetail("");

        if (!navigator?.mediaDevices?.getUserMedia) {
            setDetail("Your browser does not support camera access. Try Chrome or Edge.");
            setPhase("error");
            return;
        }

        function tryFallback() {
            navigator.mediaDevices.getUserMedia({ video: true, audio: false })
                .then((stream) => {
                    if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return; }
                    streamRef.current?.getTracks().forEach((t) => t.stop());
                    streamRef.current = stream;
                    if (videoRef.current) videoRef.current.srcObject = stream;
                    setCountdown(3);
                    setPhase("countdown");
                })
                .catch(() => {
                    if (!cancelled) {
                        setDetail("Could not access camera. Ensure no other app is using it, then press Retry.");
                        setPhase("error");
                    }
                });
        }

        navigator.mediaDevices
            .getUserMedia({ video: { facingMode: "user", width: 640, height: 480 }, audio: false })
            .then((stream) => {
                if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return; }
                streamRef.current?.getTracks().forEach((t) => t.stop());
                streamRef.current = stream;
                if (videoRef.current) videoRef.current.srcObject = stream;
                setCountdown(3);
                setPhase("countdown");
            })
            .catch((err: unknown) => {
                if (cancelled) return;
                const name = err instanceof DOMException ? err.name : "";
                if (name === "NotAllowedError" || name === "PermissionDeniedError") {
                    setDetail(
                        "Camera access denied.\n" +
                        "Click the camera icon in your browser address bar and choose Allow, then press Retry."
                    );
                    setPhase("error");
                } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
                    setDetail("No camera found. Please connect a webcam and try again.");
                    setPhase("error");
                } else if (name === "NotReadableError" || name === "TrackStartError") {
                    setDetail("Camera is in use by another application. Close it and press Retry.");
                    setPhase("error");
                } else if (name === "OverconstrainedError") {
                    tryFallback();
                } else {
                    setDetail(`Camera error (${name || "unknown"}). Please press Retry.`);
                    setPhase("error");
                }
            });

        return () => {
            cancelled = true;
            streamRef.current?.getTracks().forEach((t) => t.stop());
            streamRef.current = null;
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [cameraKey]);

    // ── Countdown → auto-capture ──────────────────────────────────────────────
    useEffect(() => {
        if (phase !== "countdown") return;
        if (countdown <= 0) {
            void doCapture();
            return;
        }
        const id = setTimeout(() => setCountdown((c) => c - 1), 1000);
        return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [phase, countdown]);

    const doCapture = useCallback(async () => {
        if (!videoRef.current || !streamRef.current) return;

        setFlash(true);
        setTimeout(() => setFlash(false), 200);

        const image = captureBase64(videoRef.current);
        setPhase("verifying");

        try {
            const res  = await fetch("/api/face-auth/verify", {
                method:      "POST",
                credentials: "include",
                headers:     { "Content-Type": "application/json" },
                body:        JSON.stringify({ image }),
            });
            const data = await res.json();

            if (data.verified) {
                setConfidence(data.confidence ?? 0);
                streamRef.current?.getTracks().forEach((t) => t.stop());
                setPhase("success");
                setTimeout(() => onSuccess(), 1000);
            } else {
                setDetail(data.detail ?? data.reason ?? "Face not recognised. Please try again.");
                setPhase("failed");
            }
        } catch {
            setDetail("Network error. Please try again.");
            setPhase("failed");
        }
    }, [onSuccess]);

    function retry() {
        setCameraKey((k) => k + 1);
    }

    const ovalColor =
        phase === "success"   ? "border-emerald-400/80" :
        phase === "failed"    ? "border-rose-400/60"    :
        phase === "verifying" ? "border-amber-400/60"   :
                                "border-sky-400/60";

    return (
        <div className="space-y-5">
            <div className="text-center">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-sky-600/20 mb-3">
                    <ScanFace className="size-6 text-sky-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-100">Face verification</h3>
                <p className="text-sm text-slate-400 mt-1">
                    Look directly at the camera — we&apos;ll verify it&apos;s you automatically.
                </p>
            </div>

            <div
                className={`relative mx-auto w-full max-w-xs aspect-[4/3] rounded-2xl overflow-hidden bg-slate-950 border border-slate-700 transition-all duration-200 ${flash ? "brightness-[2]" : ""}`}
            >
                <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover scale-x-[-1]" />

                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className={`w-40 h-52 rounded-full border-2 ${ovalColor} transition-colors duration-300 ${phase === "countdown" ? "animate-pulse" : ""}`} />
                </div>

                {phase === "init" && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/80">
                        <Loader2 className="size-8 text-sky-400 animate-spin mb-2" />
                        <span className="text-sm text-slate-300">Starting camera…</span>
                    </div>
                )}

                {phase === "error" && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/90 px-4 gap-1.5">
                        <XCircle className="size-8 text-rose-400 shrink-0" />
                        {detail.split("\n").map((line, i) => (
                            <span key={i} className="text-xs text-slate-300 text-center">{line}</span>
                        ))}
                    </div>
                )}

                {phase === "countdown" && countdown > 0 && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                        <span className="text-7xl font-bold text-white/80 drop-shadow-lg tabular-nums leading-none">{countdown}</span>
                        <span className="text-sm text-slate-300 mt-2">Hold still…</span>
                    </div>
                )}

                {phase === "verifying" && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/75">
                        <Loader2 className="size-8 text-sky-400 animate-spin mb-2" />
                        <span className="text-sm text-slate-300">Verifying your identity…</span>
                    </div>
                )}

                {phase === "success" && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-emerald-900/80">
                        <CheckCircle2 className="size-12 text-emerald-400 mb-2" />
                        <span className="text-base font-semibold text-emerald-200">Identity confirmed</span>
                        <span className="text-xs text-emerald-400 mt-1">{Math.round(confidence * 100)}% confidence</span>
                    </div>
                )}

                {phase === "failed" && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-rose-900/70 px-4">
                        <XCircle className="size-10 text-rose-400 mb-2" />
                        <span className="text-sm font-semibold text-rose-200 text-center">{detail}</span>
                    </div>
                )}
            </div>

            {phase === "countdown" && countdown > 0 && (
                <p className="text-center text-sm text-slate-400">
                    Centre your face in the oval — capturing in <span className="text-sky-400 font-semibold">{countdown}</span>s
                </p>
            )}

            {phase === "failed" && (
                <div className="space-y-2">
                    <RBButton className="w-full" onClick={retry}>
                        <Camera className="size-4" /> Try again
                    </RBButton>
                    <button type="button" onClick={onFallback} className="w-full text-sm text-slate-500 hover:text-slate-300 transition-colors text-center py-1">
                        Use OTP code instead
                    </button>
                </div>
            )}

            {phase === "error" && (
                <div className="space-y-2">
                    <RBButton className="w-full" onClick={retry}>
                        <Camera className="size-4" /> Retry camera access
                    </RBButton>
                    <button type="button" onClick={onFallback} className="w-full text-sm text-slate-400 hover:text-slate-200 transition-colors text-center py-1">
                        Use OTP code instead
                    </button>
                </div>
            )}

            {phase === "countdown" && (
                <button type="button" onClick={onFallback} className="w-full text-xs text-slate-600 hover:text-slate-400 transition-colors text-center">
                    Use OTP code instead
                </button>
            )}
        </div>
    );
}

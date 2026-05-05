"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, CheckCircle2, Loader2, X, XCircle } from "lucide-react";
import { RBButton } from "@/components/reactbits";

type Phase = "init" | "idle" | "capturing" | "enrolling" | "success" | "failed" | "error";

interface FaceEnrollModalProps {
    onClose: () => void;
    onEnrolled: () => void;
}

function captureBase64(video: HTMLVideoElement): string {
    const canvas = document.createElement("canvas");
    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")!.drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.85).split(",")[1];
}

export default function FaceEnrollModal({ onClose, onEnrolled }: FaceEnrollModalProps) {
    const videoRef  = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const [phase,   setPhase]   = useState<Phase>("init");
    const [detail,  setDetail]  = useState("");

    useEffect(() => {
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
    }, []);

    const capture = useCallback(async () => {
        if (!videoRef.current) return;
        const b64 = captureBase64(videoRef.current);
        setPhase("enrolling");
        setDetail("");

        // 90-second timeout — the AI model may need to download on first use
        const controller = new AbortController();
        const timeoutId  = setTimeout(() => controller.abort(), 90_000);

        try {
            const res = await fetch("/api/face-auth/enroll", {
                method: "POST",
                signal: controller.signal,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image: b64 }),
            });
            clearTimeout(timeoutId);
            const data = await res.json();
            if (data.success) {
                setPhase("success");
                streamRef.current?.getTracks().forEach((t) => t.stop());
                setTimeout(onEnrolled, 1200);
            } else {
                setDetail(data.detail ?? data.reason ?? "Enrollment failed.");
                setPhase("failed");
            }
        } catch (err: unknown) {
            clearTimeout(timeoutId);
            if (err instanceof Error && err.name === "AbortError") {
                setDetail("The AI model is still loading in the background. Please wait 30 seconds and try again.");
            } else {
                setDetail("Network error during enrollment.");
            }
            setPhase("failed");
        }
    }, [onEnrolled]);

    return (
        /* Modal backdrop */
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
            <div className="relative w-full max-w-sm bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-5 shadow-2xl">
                {/* Close */}
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 text-slate-500 hover:text-slate-200 transition-colors"
                >
                    <X className="size-5" />
                </button>

                <div className="text-center">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-sky-600/20 mb-3">
                        <Camera className="size-6 text-sky-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-100">Enroll face</h3>
                    <p className="text-sm text-slate-400 mt-1">
                        Centre your face in the frame. Make sure lighting is good and you are alone.
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
                    {phase === "enrolling" && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/80 px-4">
                            <Loader2 className="size-7 text-sky-400 animate-spin mb-2" />
                            <span className="text-sm text-slate-300 text-center">Analysing your face…</span>
                            <span className="text-xs text-slate-500 text-center mt-1">This may take up to 30 s on first use</span>
                        </div>
                    )}
                    {phase === "success" && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-emerald-900/80">
                            <CheckCircle2 className="size-9 text-emerald-400 mb-2" />
                            <span className="text-sm font-semibold text-emerald-200">Face enrolled!</span>
                        </div>
                    )}
                </div>

                {phase === "failed" && detail && (
                    <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-sm text-rose-400 text-center">
                        {detail}
                    </div>
                )}

                {phase === "idle" && (
                    <RBButton className="w-full" onClick={capture}>
                        <Camera className="size-4" />
                        Capture &amp; enroll
                    </RBButton>
                )}
                {phase === "failed" && (
                    <div className="space-y-2">
                        <RBButton className="w-full" onClick={() => { setDetail(""); setPhase("idle"); }}>
                            Try again
                        </RBButton>
                        <RBButton variant="secondary" className="w-full" onClick={onClose}>
                            Cancel
                        </RBButton>
                    </div>
                )}
                {(phase === "enrolling" || phase === "init") && (
                    <RBButton className="w-full" disabled>
                        <Loader2 className="size-4 animate-spin" />
                        Please wait…
                    </RBButton>
                )}
            </div>
        </div>
    );
}

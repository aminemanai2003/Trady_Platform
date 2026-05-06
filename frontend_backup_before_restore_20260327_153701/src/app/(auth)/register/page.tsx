"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { TrendingUp, Loader2, Eye, EyeOff, CheckCircle2 } from "lucide-react";

export default function RegisterPage() {
    const router = useRouter();
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPw, setShowPw] = useState(false);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        setLoading(true);

        if (password.length < 6) {
            setError("Password must be at least 6 characters");
            setLoading(false);
            return;
        }

        const res = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, password }),
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

        setLoading(false);

        if (signInRes?.ok) {
            router.push("/dashboard");
            router.refresh();
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-[#0a1929] via-[#0d1f2d] to-[#183D53] flex items-center justify-center p-4">
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute top-[-20%] right-[-10%] w-[500px] h-[500px] bg-[#4D8048]/12 rounded-full blur-[120px]" />
                <div className="absolute bottom-[-10%] left-[-5%] w-[400px] h-[400px] bg-[#0658BA]/12 rounded-full blur-[100px]" />
            </div>

            <div className="relative z-10 w-full max-w-md">
                <div className="flex items-center justify-center gap-3 mb-8">
                    <img src="/logo.png" alt="Trady" className="h-10 w-auto" />
                    <span className="text-xl font-bold text-white">Trady</span>
                </div>

                <div className="bg-slate-900/40 border border-slate-700/50 rounded-2xl p-8 backdrop-blur-xl shadow-2xl">
                    <h2 className="text-2xl font-bold text-white text-center mb-1">Create your account</h2>
                    <p className="text-sm text-slate-400 text-center mb-6">Start generating alpha signals today</p>

                    {error && (
                        <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-sm text-rose-400 text-center">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">Name</label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="w-full px-4 py-3 rounded-xl bg-slate-900/50 border border-slate-700/50 text-white placeholder:text-slate-400 focus:outline-none focus:border-[#4D8048]/60 focus:ring-2 focus:ring-[#4D8048]/30 transition-all"
                                placeholder="Your name"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                className="w-full px-4 py-3 rounded-xl bg-slate-900/50 border border-slate-700/50 text-white placeholder:text-slate-400 focus:outline-none focus:border-[#4D8048]/60 focus:ring-2 focus:ring-[#4D8048]/30 transition-all"
                                placeholder="trader@example.com"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
                            <div className="relative">
                                <input
                                    type={showPw ? "text" : "password"}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    className="w-full px-4 py-3 rounded-xl bg-slate-900/50 border border-slate-700/50 text-white placeholder:text-slate-400 focus:outline-none focus:border-[#4D8048]/60 focus:ring-2 focus:ring-[#4D8048]/30 transition-all pr-11"
                                    placeholder="Min 6 characters"
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

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3 rounded-xl bg-gradient-to-r from-[#4D8048] via-[#0658BA] to-[#0658BA] text-white font-semibold hover:scale-[1.02] hover:shadow-2xl hover:shadow-[#4D8048]/40 transition-all shadow-lg shadow-[#0658BA]/30 disabled:opacity-50 flex items-center justify-center gap-2"
                        >
                            {loading ? <Loader2 className="size-4 animate-spin" /> : null}
                            {loading ? "Creating account..." : "Create Account"}
                        </button>
                    </form>

                    <div className="mt-6 space-y-2">
                        {["4 AI agent signals", "Real-time analytics", "Risk management tools"].map((f) => (
                            <div key={f} className="flex items-center gap-2 text-xs text-slate-400">
                                <CheckCircle2 className="size-3.5 text-green-400" />
                                {f}
                            </div>
                        ))}
                    </div>

                    <p className="text-sm text-slate-400 text-center mt-6">
                        Already have an account?{" "}
                        <Link href="/login" className="text-green-400 hover:text-[#4D8048] font-medium transition-colors">
                            Sign in
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}

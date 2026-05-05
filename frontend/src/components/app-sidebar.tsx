"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { useEffect, useRef, useState } from "react";
import {
    Sidebar,
    SidebarContent,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarFooter,
    SidebarGroup,
    SidebarGroupLabel,
    SidebarGroupContent,
    SidebarSeparator,
} from "@/components/ui/sidebar";
import {
    LayoutDashboard,
    Bot,
    BarChart3,
    FileText,
    Activity,
    CandlestickChart,
    Monitor,
    Settings,
    LogOut,
    GraduationCap,
    Wifi,
    FlaskConical,
    Accessibility,
} from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useAccessibility, type FontScale, type ContrastMode, type ColorBlindMode, type CursorSize, type LineSpacing } from "@/components/accessibility-provider";

/* ── Accessibility quick panel ───────────────────────────────────────────── */
function AccessibilityPanel({ onClose }: { onClose: () => void }) {
    const {
        fontScale, contrast, reducedMotion, dyslexicFont,
        textToSpeech, colorBlindMode, cursorSize, highlightLinks, lineSpacing,
        isSpeaking,
        setFontScale, setContrast, setReducedMotion, setDyslexicFont,
        setTextToSpeech, setColorBlindMode, setCursorSize, setHighlightLinks, setLineSpacing,
        speak, stopSpeech,
    } = useAccessibility();
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node)) {
                onClose();
            }
        }
        document.addEventListener("mousedown", handleClick);
        return () => document.removeEventListener("mousedown", handleClick);
    }, [onClose]);

    const Toggle = ({ on, onClick, label }: { on: boolean; onClick: () => void; label: string }) => (
        <button
            aria-pressed={on}
            aria-label={label}
            onClick={onClick}
            className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue-500/40 ${on ? "bg-brand-blue-600" : "bg-slate-700"}`}
        >
            <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${on ? "translate-x-4" : "translate-x-0.5"}`} />
        </button>
    );

    function readPage() {
        const text = document.body.innerText.slice(0, 1000);
        speak(text);
    }

    return (
        <div
            ref={ref}
            role="dialog"
            aria-label="Accessibility settings"
            className="absolute bottom-full left-2 right-2 mb-2 z-50 rounded-xl border border-white/10 bg-[#0f1825]/95 backdrop-blur-xl shadow-2xl p-4 space-y-4 max-h-[80vh] overflow-y-auto"
        >
            <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white tracking-wide">Accessibility</span>
                <button onClick={onClose} aria-label="Close" className="text-slate-500 hover:text-white text-xs leading-none">✕</button>
            </div>

            {/* Font size */}
            <div className="space-y-1.5">
                <span className="text-[10px] text-slate-500 uppercase tracking-widest">Font size</span>
                <div className="grid grid-cols-4 gap-1">
                    {([1, 1.1, 1.2, 1.3] as FontScale[]).map((s) => (
                        <button
                            key={s}
                            aria-pressed={fontScale === s}
                            onClick={() => setFontScale(s)}
                            className={`rounded-md py-1.5 text-[11px] font-medium transition-colors ${fontScale === s ? "bg-brand-blue-600 text-white" : "bg-white/[0.05] text-slate-400 hover:bg-white/10"}`}
                        >
                            {s === 1 ? "A" : s === 1.1 ? "A+" : s === 1.2 ? "A++" : "A+++"}
                        </button>
                    ))}
                </div>
            </div>

            {/* Contrast */}
            <div className="space-y-1.5">
                <span className="text-[10px] text-slate-500 uppercase tracking-widest">Contrast</span>
                <div className="grid grid-cols-2 gap-1">
                    {(["default", "high"] as ContrastMode[]).map((m) => (
                        <button
                            key={m}
                            aria-pressed={contrast === m}
                            onClick={() => setContrast(m)}
                            className={`rounded-md py-1.5 text-[11px] font-medium capitalize transition-colors ${contrast === m ? "bg-brand-blue-600 text-white" : "bg-white/[0.05] text-slate-400 hover:bg-white/10"}`}
                        >
                            {m === "default" ? "Default" : "High"}
                        </button>
                    ))}
                </div>
            </div>

            {/* Color-blind mode */}
            <div className="space-y-1.5">
                <span className="text-[10px] text-slate-500 uppercase tracking-widest">Color vision</span>
                <div className="grid grid-cols-2 gap-1">
                    {(["none", "deuteranopia", "protanopia", "tritanopia"] as ColorBlindMode[]).map((m) => (
                        <button
                            key={m}
                            aria-pressed={colorBlindMode === m}
                            onClick={() => setColorBlindMode(m)}
                            className={`rounded-md py-1.5 text-[10px] font-medium capitalize transition-colors ${colorBlindMode === m ? "bg-brand-blue-600 text-white" : "bg-white/[0.05] text-slate-400 hover:bg-white/10"}`}
                        >
                            {m === "none" ? "Normal" : m === "deuteranopia" ? "Green-blind" : m === "protanopia" ? "Red-blind" : "Blue-blind"}
                        </button>
                    ))}
                </div>
            </div>

            {/* Line spacing */}
            <div className="space-y-1.5">
                <span className="text-[10px] text-slate-500 uppercase tracking-widest">Line spacing</span>
                <div className="grid grid-cols-3 gap-1">
                    {(["default", "relaxed", "loose"] as LineSpacing[]).map((s) => (
                        <button
                            key={s}
                            aria-pressed={lineSpacing === s}
                            onClick={() => setLineSpacing(s)}
                            className={`rounded-md py-1.5 text-[10px] font-medium capitalize transition-colors ${lineSpacing === s ? "bg-brand-blue-600 text-white" : "bg-white/[0.05] text-slate-400 hover:bg-white/10"}`}
                        >
                            {s.charAt(0).toUpperCase() + s.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            {/* Cursor size */}
            <div className="space-y-1.5">
                <span className="text-[10px] text-slate-500 uppercase tracking-widest">Cursor size</span>
                <div className="grid grid-cols-3 gap-1">
                    {(["default", "large", "x-large"] as CursorSize[]).map((s) => (
                        <button
                            key={s}
                            aria-pressed={cursorSize === s}
                            onClick={() => setCursorSize(s)}
                            className={`rounded-md py-1.5 text-[10px] font-medium transition-colors ${cursorSize === s ? "bg-brand-blue-600 text-white" : "bg-white/[0.05] text-slate-400 hover:bg-white/10"}`}
                        >
                            {s === "default" ? "Default" : s === "large" ? "Large" : "X-Large"}
                        </button>
                    ))}
                </div>
            </div>

            {/* Toggles */}
            <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                    <span className="text-[11px] text-slate-300">Reduced motion</span>
                    <Toggle label="Toggle reduced motion" on={reducedMotion} onClick={() => setReducedMotion(!reducedMotion)} />
                </div>
                <div className="flex items-center justify-between">
                    <span className="text-[11px] text-slate-300">Dyslexia font</span>
                    <Toggle label="Toggle dyslexia font" on={dyslexicFont} onClick={() => setDyslexicFont(!dyslexicFont)} />
                </div>
                <div className="flex items-center justify-between">
                    <span className="text-[11px] text-slate-300">Highlight links</span>
                    <Toggle label="Toggle highlight links" on={highlightLinks} onClick={() => setHighlightLinks(!highlightLinks)} />
                </div>
                <div className="flex items-center justify-between">
                    <span className="text-[11px] text-slate-300">Read selected text 🔊</span>
                    <Toggle label="Toggle text to speech on selection" on={textToSpeech} onClick={() => setTextToSpeech(!textToSpeech)} />
                </div>
            </div>

            {/* TTS quick read */}
            <div className="flex gap-1 pt-1 border-t border-white/[0.07]">
                <button
                    onClick={readPage}
                    className="flex-1 rounded-md bg-white/[0.05] hover:bg-white/10 text-slate-300 text-[10px] py-1.5 transition-colors"
                >
                    🔊 Read page
                </button>
                {isSpeaking && (
                    <button
                        onClick={stopSpeech}
                        className="rounded-md bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-[10px] py-1.5 px-2 transition-colors"
                    >
                        ⏹ Stop
                    </button>
                )}
            </div>
        </div>
    );
}

/* ── Grouped navigation ──────────────────────────────────────────────────── */
const navGroups = [
    {
        label: "Overview",
        items: [
            { title: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
        ],
    },
    {
        label: "Trading",
        items: [
            { title: "Trading",        href: "/trading",   icon: CandlestickChart },
            { title: "Agent Monitor",  href: "/agents",    icon: Bot },
            { title: "Testing",        href: "/testing",   icon: FlaskConical },
        ],
    },
    {
        label: "Intelligence",
        items: [
            { title: "Analytics",       href: "/analytics",       icon: BarChart3 },
            { title: "Reports",         href: "/reports",         icon: FileText },
            { title: "Strategy Tutor",  href: "/strategy-tutor",  icon: GraduationCap },
            { title: "Backtesting",     href: "/backtesting",     icon: Activity },
        ],
    },
    {
        label: "System",
        items: [
            { title: "Monitoring", href: "/monitoring", icon: Monitor },
            { title: "Settings",   href: "/settings",   icon: Settings },
        ],
    },
];

export function AppSidebar() {
    const pathname = usePathname();
    const { data: session } = useSession();
    const [a11yOpen, setA11yOpen] = useState(false);

    const initials = session?.user?.name
        ? session.user.name
              .split(" ")
              .map((n) => n[0])
              .join("")
              .toUpperCase()
              .slice(0, 2)
        : session?.user?.email?.charAt(0).toUpperCase() || "U";

    const displayName = session?.user?.name || "Trader";
    const displayEmail = session?.user?.email || "";

    async function handleLogout() {
        await fetch("/api/django-auth/logout", { method: "POST" });
        await signOut({ callbackUrl: "/login" });
    }

    return (
        <Sidebar collapsible="icon" variant="inset">
            <SidebarHeader>
                <SidebarMenu>
                    <SidebarMenuItem>
                        <SidebarMenuButton size="lg" asChild>
                            <Link href="/">
                                <Image src="/logo.png" alt="Trady" width={32} height={32} className="flex aspect-square h-8 w-auto" />
                                <div className="grid flex-1 text-left text-sm leading-tight">
                                    <span className="truncate font-bold">Trady</span>
                                    <span className="truncate text-xs text-muted-foreground">
                                        Multi-Agent Platform
                                    </span>
                                </div>
                            </Link>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarHeader>

            <SidebarContent>
                {navGroups.map((group, gi) => (
                    <SidebarGroup key={group.label}>
                        {gi > 0 && <SidebarSeparator className="mb-2 bg-white/5" />}
                        <SidebarGroupLabel className="text-[10px] tracking-widest uppercase text-muted-foreground/60">
                            {group.label}
                        </SidebarGroupLabel>
                        <SidebarGroupContent>
                            <SidebarMenu>
                                {group.items.map((item) => {
                                    const isActive = pathname === item.href;
                                    return (
                                        <SidebarMenuItem key={item.title}>
                                            <SidebarMenuButton
                                                asChild
                                                isActive={isActive}
                                                tooltip={item.title}
                                                aria-current={isActive ? "page" : undefined}
                                                className={isActive
                                                    ? "bg-brand-blue-600/15 text-brand-blue-300 hover:bg-brand-blue-600/20 hover:text-brand-blue-200 [&_svg]:text-brand-blue-400"
                                                    : "hover:bg-white/[0.05]"
                                                }
                                            >
                                                <Link href={item.href}>
                                                    <item.icon />
                                                    <span>{item.title}</span>
                                                </Link>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                    );
                                })}
                            </SidebarMenu>
                        </SidebarGroupContent>
                    </SidebarGroup>
                ))}
            </SidebarContent>

            <SidebarFooter>
                <SidebarMenu>
                    {/* Accessibility quick-access */}
                    <SidebarMenuItem className="relative">
                        {a11yOpen && <AccessibilityPanel onClose={() => setA11yOpen(false)} />}
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <SidebarMenuButton
                                    size="sm"
                                    onClick={() => setA11yOpen((o) => !o)}
                                    className={`transition-colors ${a11yOpen ? "bg-brand-blue-600/20 text-brand-blue-300" : "text-slate-400 hover:text-white hover:bg-white/[0.05]"}`}
                                >
                                    <Accessibility className="size-4" />
                                    <span className="text-xs">Accessibility</span>
                                </SidebarMenuButton>
                            </TooltipTrigger>
                            <TooltipContent side="top" className="text-xs">
                                Accessibility settings
                            </TooltipContent>
                        </Tooltip>
                    </SidebarMenuItem>

                    {/* System status */}
                    <SidebarMenuItem>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <SidebarMenuButton size="sm" className="cursor-default opacity-70 hover:opacity-100">
                                    <Wifi className="size-4 text-brand-green-500" />
                                    <span className="text-xs text-muted-foreground">System Online</span>
                                    <span className="ml-auto size-2 rounded-full bg-brand-green-500 animate-pulse" />
                                </SidebarMenuButton>
                            </TooltipTrigger>
                            <TooltipContent side="top" className="text-xs">
                                All backend services operational
                            </TooltipContent>
                        </Tooltip>
                    </SidebarMenuItem>

                    {/* User info */}
                    <SidebarMenuItem>
                        <div className="flex items-center gap-3 px-3 py-2 border-t border-white/[0.07]">
                            <Avatar className="h-8 w-8 border-2 border-brand-blue-600/50 shrink-0">
                                <AvatarFallback className="bg-gradient-to-br from-brand-green-600 to-brand-blue-600 text-white font-semibold text-xs">
                                    {initials}
                                </AvatarFallback>
                            </Avatar>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-semibold text-white truncate" title={displayName}>
                                    {displayName}
                                </p>
                                <p className="text-xs text-slate-400 truncate" title={displayEmail}>
                                    {displayEmail}
                                </p>
                            </div>
                        </div>
                    </SidebarMenuItem>

                    {/* Logout */}
                    <SidebarMenuItem>
                        <SidebarMenuButton
                            onClick={() => void handleLogout()}
                            data-testid="sidebar-logout"
                            className="text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors"
                        >
                            <LogOut className="size-4" />
                            <span>Log out</span>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarFooter>
        </Sidebar>
    );
}



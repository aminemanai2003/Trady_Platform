"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
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
} from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

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



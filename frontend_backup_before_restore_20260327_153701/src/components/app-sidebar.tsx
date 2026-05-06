"use client";

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
} from "@/components/ui/sidebar";
import {
    LayoutDashboard,
    Bot,
    BarChart3,
    FileText,
    Activity,
    TrendingUp,
    FlaskConical,
    LogOut,
    Users,
} from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const navItems = [
    { title: "Dashboard",   href: "/dashboard",   icon: LayoutDashboard, badge: "BO1–BO5",   gradient: "from-violet-500 to-indigo-500" },
    { title: "Signal Lab",  href: "/agents",      icon: Bot,             badge: "DSO1+2+3", gradient: "from-emerald-500 to-teal-500"  },
    { title: "Analytics",   href: "/analytics",   icon: BarChart3,       badge: "DSO2.2",   gradient: "from-blue-500 to-cyan-500"     },
    { title: "Backtesting", href: "/backtesting", icon: TrendingUp,      badge: "DSO2.2+3", gradient: "from-amber-500 to-orange-500"  },
    { title: "Feature Lab", href: "/features",    icon: FlaskConical,    badge: "DSO1.2",   gradient: "from-fuchsia-500 to-pink-500"  },
    { title: "Monitoring",  href: "/monitoring",  icon: Activity,        badge: "DSO4",     gradient: "from-rose-500 to-red-500"      },
    { title: "Reports",     href: "/reports",     icon: FileText,        badge: "DSO5.1",   gradient: "from-sky-500 to-blue-500"      },
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

    return (
        <Sidebar collapsible="icon" variant="inset">
            <SidebarHeader>
                <SidebarMenu>
                    <SidebarMenuItem>
                        <SidebarMenuButton size="lg" asChild>
                            <Link href="/">
                                <div className="flex aspect-square size-8 items-center justify-center rounded-lg overflow-hidden shadow-lg border border-white/10">
                                    <img src="/logo.png" alt="Trady" className="size-8 object-cover" onError={(e)=>{(e.currentTarget as HTMLImageElement).style.display='none'; e.currentTarget.parentElement!.innerHTML='<span class="text-white font-black text-xs">T</span>';}}/>
                                </div>
                                <div className="grid flex-1 text-left text-sm leading-tight">
                                    <span className="truncate font-bold text-white">Trady</span>
                                    <span className="truncate text-[10px] text-slate-400">
                                        Multi-Agent Forex IA
                                    </span>
                                </div>
                            </Link>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarHeader>

            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupLabel className="text-[10px] uppercase tracking-widest text-slate-500">
                        DS Objectives
                    </SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {navItems.map((item) => {
                                const isActive = pathname === item.href;
                                return (
                                    <SidebarMenuItem key={item.title}>
                                        <SidebarMenuButton
                                            asChild
                                            isActive={isActive}
                                            tooltip={`${item.title} · ${item.badge}`}
                                        >
                                            <Link href={item.href} className="flex items-center gap-2.5">
                                                <div className={`flex size-6 shrink-0 items-center justify-center rounded-md bg-gradient-to-br ${item.gradient} shadow-sm`}>
                                                    <item.icon className="size-3.5 text-white" />
                                                </div>
                                                <span className="text-sm flex-1">{item.title}</span>
                                                <span className="text-[9px] font-mono text-slate-500">{item.badge}</span>
                                            </Link>
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                );
                            })}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>

                <SidebarGroup className="mt-2">
                    <SidebarGroupContent>
                        <div className="px-2 py-1.5 rounded-lg bg-white/[0.03] border border-white/5">
                            <div className="flex items-center gap-1.5 mb-1">
                                <Users className="size-3 text-slate-500" />
                                <span className="text-[10px] font-bold text-slate-400">DATAMINDS</span>
                            </div>
                            <div className="text-[9px] font-mono leading-relaxed text-slate-600">
                                Chtioui · Manai · Fersi<br />Chairat · Aloui
                            </div>
                        </div>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>

            <SidebarFooter>
                <SidebarMenu>
                    <SidebarMenuItem>
                        <SidebarMenuButton
                            onClick={() => signOut({ callbackUrl: "/" })}
                            className="text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                            tooltip="Sign out"
                        >
                            <LogOut className="size-4" />
                            <span>Sign Out</span>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
                <div className="flex items-center gap-2.5 px-2 py-2 border-t border-white/5 mt-1">
                    <Avatar className="size-7 border border-white/10">
                        <AvatarFallback className="bg-gradient-to-br from-violet-600 to-blue-600 text-white text-[10px] font-bold">
                            {initials}
                        </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium truncate">
                            {session?.user?.name || session?.user?.email?.split("@")[0] || "User"}
                        </div>
                        <div className="text-[10px] text-slate-500 truncate">{session?.user?.email}</div>
                    </div>
                </div>
            </SidebarFooter>
        </Sidebar>
    );
}

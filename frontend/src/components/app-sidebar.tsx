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
    CandlestickChart,
    Monitor,
    Settings,
    LogOut,
    User,
} from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const navItems = [
    { title: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { title: "Trading", href: "/trading", icon: CandlestickChart },
    { title: "Agent Monitor", href: "/agents", icon: Bot },
    { title: "Analytics", href: "/analytics", icon: BarChart3 },
    { title: "Reports", href: "/reports", icon: FileText },
    { title: "Monitoring", href: "/monitoring", icon: Monitor },
    { title: "Settings", href: "/settings", icon: Settings },
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
                                <img src="/logo.png" alt="Trady" className="flex aspect-square h-8 w-auto" />
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
                <SidebarGroup>
                    <SidebarGroupLabel>Navigation</SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {navItems.map((item) => (
                                <SidebarMenuItem key={item.title}>
                                    <SidebarMenuButton
                                        asChild
                                        isActive={pathname === item.href}
                                        tooltip={item.title}
                                    >
                                        <Link href={item.href}>
                                            <item.icon />
                                            <span>{item.title}</span>
                                        </Link>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            ))}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>

            <SidebarFooter>
                <SidebarMenu>
                    <SidebarMenuItem>
                        <div className="flex items-center gap-3 px-3 py-2 border-t border-slate-700/50">
                            <Avatar className="h-8 w-8 border-2 border-[#4D8048]">
                                <AvatarFallback className="bg-gradient-to-br from-[#4D8048] to-[#0658BA] text-white font-semibold text-xs">
                                    {initials}
                                </AvatarFallback>
                            </Avatar>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-semibold text-white truncate">
                                    {session?.user?.name || "Trader"}
                                </p>
                                <p className="text-xs text-slate-400 truncate">
                                    {session?.user?.email}
                                </p>
                            </div>
                        </div>
                    </SidebarMenuItem>
                    <SidebarMenuItem>
                        <SidebarMenuButton
                            onClick={() => signOut({ callbackUrl: "/login" })}
                            className="text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                        >
                            <LogOut className="size-4" />
                            <span>Log out</span>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                    <SidebarMenuItem>
                        <SidebarMenuButton size="sm">
                            <Activity className="size-4 text-[#4D8048]" />
                            <span className="text-xs text-muted-foreground">
                                System Online
                            </span>
                            <span className="ml-auto size-2 rounded-full bg-[#4D8048] animate-pulse" />
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarFooter>
        </Sidebar>
    );
}


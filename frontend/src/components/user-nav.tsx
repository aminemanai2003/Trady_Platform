"use client";

import { useSession, signOut } from "next-auth/react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CreditCard, LogOut, Shield } from "lucide-react";
import Link from "next/link";

export function UserNav() {
    const { data: session } = useSession();

    async function handleLogout() {
        await fetch("/api/django-auth/logout", { method: "POST" });
        await signOut({ callbackUrl: "/login" });
    }

    if (!session?.user) {
        return null;
    }

    const initials = session.user.name
        ? session.user.name
              .split(" ")
              .map((n) => n[0])
              .join("")
              .toUpperCase()
              .slice(0, 2)
        : session.user.email?.charAt(0).toUpperCase() || "U";
    const displayName = session.user.name || "Trader";
    const displayImage = session.user.image || "";

    return (
        <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-slate-800/50 transition-colors">
                <Avatar className="h-8 w-8 border-2 border-[#4D8048]">
                    {displayImage ? <AvatarImage src={displayImage} alt={displayName} /> : null}
                    <AvatarFallback className="bg-gradient-to-br from-[#4D8048] to-[#0658BA] text-white font-semibold text-sm">
                        {initials}
                    </AvatarFallback>
                </Avatar>
                <div className="flex flex-col items-start text-left">
                    <span className="text-sm font-semibold text-white">
                        {displayName}
                    </span>
                    <span className="text-xs text-slate-400">
                        {session.user.email}
                    </span>
                </div>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56 bg-slate-900 border-slate-700">
                <DropdownMenuLabel className="text-slate-300">
                    My Account
                </DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-slate-700" />
                <DropdownMenuItem asChild className="cursor-pointer hover:bg-slate-800">
                    <Link href="/billing" className="flex items-center gap-2">
                        <CreditCard className="size-4" />
                        Billing
                    </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild className="cursor-pointer hover:bg-slate-800">
                    <Link href="/billing" className="flex items-center gap-2">
                        <Shield className="size-4" />
                        Plan
                    </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-slate-700" />
                <DropdownMenuItem
                    onClick={() => void handleLogout()}
                    className="cursor-pointer hover:bg-slate-800 text-rose-400 focus:text-rose-400"
                >
                    <LogOut className="size-4 mr-2" />
                    Log out
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}


"use client";

import { useSession, signOut } from "next-auth/react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { User, Settings, LogOut, Shield } from "lucide-react";
import Link from "next/link";

export function UserNav() {
    const { data: session } = useSession();

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

    return (
        <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-slate-800/50 transition-colors">
                <Avatar className="h-8 w-8 border-2 border-[#4D8048]">
                    <AvatarFallback className="bg-gradient-to-br from-[#4D8048] to-[#0658BA] text-white font-semibold text-sm">
                        {initials}
                    </AvatarFallback>
                </Avatar>
                <div className="flex flex-col items-start text-left">
                    <span className="text-sm font-semibold text-white">
                        {session.user.name || "Trader"}
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
                    <Link href="/settings" className="flex items-center gap-2">
                        <User className="size-4" />
                        Profile
                    </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild className="cursor-pointer hover:bg-slate-800">
                    <Link href="/settings" className="flex items-center gap-2">
                        <Settings className="size-4" />
                        Settings
                    </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild className="cursor-pointer hover:bg-slate-800">
                    <div className="flex items-center gap-2">
                        <Shield className="size-4" />
                        Security
                    </div>
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-slate-700" />
                <DropdownMenuItem
                    onClick={() => signOut({ callbackUrl: "/login" })}
                    className="cursor-pointer hover:bg-slate-800 text-rose-400 focus:text-rose-400"
                >
                    <LogOut className="size-4 mr-2" />
                    Log out
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}

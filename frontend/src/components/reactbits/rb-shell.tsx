import * as React from "react";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

interface RBHeaderProps {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
  className?: string;
}

export function RBHeader({ title, subtitle, right, className }: RBHeaderProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-20 flex h-14 shrink-0 items-center gap-3 border-b border-border bg-background/85 px-5 backdrop-blur",
        className
      )}
    >
      <SidebarTrigger className="-ml-1 text-muted-foreground hover:bg-accent" />
      <Separator orientation="vertical" className="h-5 bg-border" />
      <div>
        <h1 className="text-base font-semibold leading-none tracking-tight text-foreground">{title}</h1>
        {subtitle ? <p className="mt-1 text-[11px] text-muted-foreground">{subtitle}</p> : null}
      </div>
      {right ? <div className="ml-auto flex items-center gap-2">{right}</div> : null}
    </header>
  );
}

export function RBContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex-1 overflow-auto p-5 md:p-6", className)} {...props} />;
}

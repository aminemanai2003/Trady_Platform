import { AppSidebar } from "@/components/app-sidebar";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { DataRefreshProvider } from "@/components/data-refresh-provider";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <TooltipProvider>
            <SidebarProvider>
                <AppSidebar />
                <SidebarInset>
                    <DataRefreshProvider>
                        {children}
                    </DataRefreshProvider>
                </SidebarInset>
            </SidebarProvider>
        </TooltipProvider>
    );
}

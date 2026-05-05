import type { Metadata } from "next";
import { Manrope, JetBrains_Mono, Sora } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { AgentCopilotPanel } from "@/components/agent-copilot/AgentCopilotPanel";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

const sora = Sora({
  variable: "--font-sora",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Trady - Multi-Agent Forex Intelligence",
  description:
    "Multi-Modal Multi-Agent Framework for Major Currency Pair Analysis and Alpha Generation.",
  icons: {
    icon: [
      { url: "/logo.png", type: "image/png" },
    ],
    shortcut: "/logo.png",
    apple: "/logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${manrope.variable} ${sora.variable} ${jetbrainsMono.variable} antialiased`}
      >
        <Providers>
          {children}
          <AgentCopilotPanel />
        </Providers>
      </body>
    </html>
  );
}



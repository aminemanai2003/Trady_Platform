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
        {/* SVG color-blind filters — hidden, referenced by CSS filter: url('#…') */}
        <svg aria-hidden="true" focusable="false" style={{ position: "absolute", width: 0, height: 0, overflow: "hidden" }}>
          <defs>
            {/* Deuteranopia (green-blind) */}
            <filter id="cb-deuteranopia-filter" colorInterpolationFilters="linearRGB">
              <feColorMatrix type="matrix" values="0.367 0.861 -0.228 0 0  0.280 0.673  0.047 0 0  -0.012 0.043  0.969 0 0  0 0 0 1 0" />
            </filter>
            {/* Protanopia (red-blind) */}
            <filter id="cb-protanopia-filter" colorInterpolationFilters="linearRGB">
              <feColorMatrix type="matrix" values="0.152 1.053 -0.205 0 0  0.115 0.786  0.099 0 0  -0.004 -0.048  1.052 0 0  0 0 0 1 0" />
            </filter>
            {/* Tritanopia (blue-blind) */}
            <filter id="cb-tritanopia-filter" colorInterpolationFilters="linearRGB">
              <feColorMatrix type="matrix" values="1.256 -0.077 -0.179 0 0  -0.078  0.931  0.148 0 0  0.005  0.691  0.304 0 0  0 0 0 1 0" />
            </filter>
          </defs>
        </svg>
        <Providers>
          {children}
          <AgentCopilotPanel />
        </Providers>
      </body>
    </html>
  );
}



import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { ThemeProvider } from "@/contexts/ThemeContext";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CyVigil - Enterprise Security Dashboard",
  description: "Monitor and protect your devices with CyVigil",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} antialiased`}>
        <ThemeProvider>
          <div className="flex min-h-screen">
            {/* Fixed Sidebar */}
            <Sidebar />
            {/* Main content with left margin to account for fixed sidebar */}
            <main className="flex-1 ml-64 min-h-screen bg-white dark:bg-black transition-colors duration-200">
              <div className="p-8">
                {children}
              </div>
            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}

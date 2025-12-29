import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

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
    <html lang="en" className="dark">
      <body className={`${inter.className} antialiased bg-black`}>
        <div className="flex min-h-screen">
          {/* Fixed Sidebar */}
          <Sidebar />
          {/* Main content with left margin to account for fixed sidebar */}
          <main className="flex-1 ml-64 min-h-screen bg-black">
            <div className="p-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}

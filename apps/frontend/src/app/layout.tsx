import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Sidebar } from "@/components/sidebar";
import { ToastProvider } from "@/context/toast-context";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], fallback: ["Arial", "sans-serif"] });

export const metadata: Metadata = {
  title: "Credit Portfolio Optimizer",
  description: "A full-stack system for optimizing pre-approved credit limits.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={inter.className}>
      <body>
        <ToastProvider>
          <div className="app-shell">
            <Sidebar />
            <main className="app-main">
              {children}
            </main>
          </div>
        </ToastProvider>
      </body>
    </html>
  );
}

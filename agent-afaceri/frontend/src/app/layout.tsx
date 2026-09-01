import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import Header from "@/components/header";

export const metadata: Metadata = {
  title: "Agent Afaceri & Juridic AI",
  description:
    "Asistent AI informativ pentru afaceri și juridic — contracte, înființare firmă, fiscalitate, GDPR, plan de afaceri.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ro">
      <body>
        <AuthProvider>
          <Header />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}

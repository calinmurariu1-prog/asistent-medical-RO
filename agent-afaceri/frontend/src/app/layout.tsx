import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent Afaceri & Juridic AI",
  description:
    "Asistent AI informativ pentru afaceri și juridic — contracte, înființare firmă, fiscalitate, plan de afaceri.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ro">
      <body>{children}</body>
    </html>
  );
}

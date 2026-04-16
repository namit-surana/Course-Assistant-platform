import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EvalAI — AI-Powered Hackathon Judging",
  description: "Evaluate teams smarter with AI-assisted rubric scoring and evidence-backed decisions.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}

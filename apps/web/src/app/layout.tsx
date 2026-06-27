import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "falsify-eval audit tool",
  description: "Local-first benchmark claim audit tool.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

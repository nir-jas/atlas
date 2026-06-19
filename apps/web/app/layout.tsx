import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Atlas",
  description: "Personal knowledge platform for learning AI Engineering",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

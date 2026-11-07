// Modified for the English text/TXT demo; scope and behavior are documented in README.md.
import "./globals.css";

export const metadata = {
  title: "Multi-Agent Contract Review",
  description: "Four-agent contract review workflow for mainland-China purchase contracts",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

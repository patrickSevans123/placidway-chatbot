import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./ui.css";

export const metadata: Metadata = {
  title: "PlacidWay guide: cancer treatment in Tijuana",
  description:
    "Ask about ITC Immunity Therapy Center: prices, what each programme includes, the doctors, and getting there. Every answer shows the page it came from.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a className="skip" href="#composer">
          Skip to the question box
        </a>
        {children}
      </body>
    </html>
  );
}

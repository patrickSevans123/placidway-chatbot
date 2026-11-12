import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./ui.css";

export const metadata: Metadata = {
  title: "PlacidWay guide: cancer treatment in Tijuana",
  description:
    "Ask about ITC Immunity Therapy Center: prices, what each programme includes, the doctors, and getting there. Every answer shows the page it came from.",
  // Their official square app icon, at the three sizes a browser or iOS asks
  // for. Opaque, so iOS has its own background when it rounds the corners.
  icons: {
    icon: [
      { url: "/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
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

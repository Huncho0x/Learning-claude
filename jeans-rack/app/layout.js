import { Instrument_Sans, Lobster } from "next/font/google";
import "./globals.css";

const sans = Instrument_Sans({ subsets: ["latin"], variable: "--font-sans" });
const script = Lobster({ subsets: ["latin"], weight: "400", variable: "--font-script" });

export const metadata = {
  title: "Rinse & Repeat — Denim on the rail",
  description: "A small denim shop. Jeans and trousers, hung up and ready.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${sans.variable} ${script.variable}`}>
      <body>{children}</body>
    </html>
  );
}

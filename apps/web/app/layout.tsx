import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";
import "./responsive.css";
import "./scenario-lab.css";
import "./workflow.css";
import "./sensitivity.css";
import "./economics.css";

export const metadata: Metadata = {
  title: "OpsTwin - Scenario Lab",
  description: "Operational Simulation and Decision Laboratory",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

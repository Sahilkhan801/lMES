"use client";

import ImmersiveFullscreenNav from "@/components/ui/immersive-full-screen-nav";

export default function ImmersiveFullscreenNavDemo() {
  return (
    <div className="w-full min-w-0">
      <ImmersiveFullscreenNav
        navConfig={{
          brand: "LMES Portal",
          brandHref: "#",
          overlayBg: "#0f172a",
          clipOrigin: "left",
        }}
        navContent={{
          agencyName: "Department of Consumer Affairs",
          tagline: "Legal Metrology Enforcement System • Govt. of India",
          location: "New Delhi, India",
          links: [
            { label: "Dashboard", href: "#" },
            { label: "Scanner & Auditor", href: "#" },
            { label: "Repository", href: "#" },
            { label: "Rules Configurator", href: "#" },
          ],
          images: [
            "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1521791136064-7986c2920216?auto=format&fit=crop&w=800&q=80",
          ],
          socials: [
            { type: "instagram", href: "#" },
            { type: "twitter", href: "#" },
            { type: "linkedin", href: "#" },
          ],
        }}
      />

      <main className="flex h-screen flex-col items-center justify-center gap-4 bg-white px-6 text-center text-black">
        <p className="text-xs uppercase tracking-[0.3em] text-black/40">Statutory Enforcement</p>
        <h1 className="max-w-2xl text-[7vw] leading-tight max-md:text-[9vw]">LMES Portal</h1>
        <p className="mt-2 max-w-md text-sm leading-relaxed text-black/60">
          Legal Metrology (Packaged Commodities) Rules, 2011 Verification & Inspection Gateway.
        </p>
      </main>
    </div>
  );
}

"use client";

import type { ReactNode } from "react";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import ProjectLogo from "@/components/ProjectLogo";

const mobileNav = [
  { href: "/", label: "Home" },
  { href: "/smart-drafter", label: "Drafter" },
  { href: "/universal-research-formatter", label: "Formatter" },
  { href: "/diagram-generator", label: "Diagram" },
  { href: "/code-to-pseudocode", label: "Pseudo" },
  { href: "/workflow", label: "Workflow" },
  { href: "/agent-hub", label: "Hub" },
  { href: "/about", label: "About" },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const pathname = usePathname();

  return (
    <div className="relative min-h-screen overflow-hidden bg-zinc-950 text-zinc-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_8%,rgba(99,102,241,0.18),transparent_34%),radial-gradient(circle_at_88%_20%,rgba(168,85,247,0.1),transparent_36%),linear-gradient(180deg,#09090b_0%,#09090b_45%,#111827_100%)]" />
      <div className="pointer-events-none absolute inset-0 opacity-[0.08] [background-image:linear-gradient(to_right,#a1a1aa_1px,transparent_1px),linear-gradient(to_bottom,#a1a1aa_1px,transparent_1px)] [background-size:34px_34px]" />

      <div className="relative mx-auto max-w-[1920px] px-0 py-0 md:px-6 md:py-6">
        <div className="sticky top-0 z-40 mb-4 border-b border-white/15 bg-black/20 px-4 py-3 backdrop-blur-xl md:px-6">
          <div className="mx-auto flex max-w-[1920px] items-center justify-between">
            <Link
              href="/about"
              className="inline-flex items-center gap-2 rounded-md border border-white/18 bg-white/[0.08] px-4 py-2 text-sm font-medium text-zinc-100 transition hover:bg-white/[0.14]"
            >
              <span className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-white/50 text-[10px] leading-none text-white/90">
                •
              </span>
              Contact us
            </Link>

            <button
              type="button"
              onClick={() => setIsMenuOpen(true)}
              aria-expanded={isMenuOpen}
              aria-controls="primary-menu-panel"
              aria-label="Open navigation menu"
              className="group inline-flex items-center gap-2 rounded-md border border-white/18 bg-white/[0.08] px-4 py-2 text-sm font-medium text-zinc-100 transition hover:bg-white/[0.14]"
            >
              Menu
              <span className="relative inline-flex h-4 w-4 flex-col items-end justify-center gap-1">
                <span className="h-px w-4 bg-zinc-100/90 transition group-hover:w-3" />
                <span className="h-px w-2.5 bg-zinc-100/90 transition group-hover:w-4" />
              </span>
            </button>
          </div>
        </div>

        <div
          className={`fixed inset-0 z-50 transition ${
            isMenuOpen
              ? "pointer-events-auto opacity-100"
              : "pointer-events-none opacity-0"
          }`}
          aria-hidden={!isMenuOpen}
        >
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setIsMenuOpen(false)}
          />

          <aside
            id="primary-menu-panel"
            className={`absolute right-0 top-0 h-full w-full max-w-md border-l border-white/10 bg-zinc-950/94 p-6 shadow-[0_0_60px_rgba(0,0,0,0.65)] backdrop-blur-2xl transition-transform duration-500 ease-out ${
              isMenuOpen ? "translate-x-0" : "translate-x-full"
            }`}
          >
            <div className="flex items-center justify-between">
              <ProjectLogo variant="compact" />
              <button
                type="button"
                onClick={() => setIsMenuOpen(false)}
                aria-label="Close navigation menu"
                className="rounded-full border border-white/15 bg-white/[0.05] px-3 py-1.5 text-sm text-zinc-100 transition hover:border-indigo-200/55 hover:bg-white/[0.1]"
              >
                Close
              </button>
            </div>

            <div className="mt-8 text-[11px] uppercase tracking-[0.24em] text-zinc-500">
              Navigation
            </div>

            <nav className="mt-4 space-y-1">
              {mobileNav.map((item, index) => {
                const active = pathname === item.href;
                const idx = `${index + 1}`.padStart(2, "0");

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setIsMenuOpen(false)}
                    className={`group flex items-center gap-4 border-b border-white/10 py-3 transition ${
                      active
                        ? "text-zinc-100"
                        : "text-zinc-300 hover:text-white"
                    }`}
                  >
                    <span className="text-xs tracking-[0.2em] text-zinc-500 transition group-hover:text-zinc-300">
                      {idx}
                    </span>
                    <span className="text-3xl font-medium leading-none tracking-tight md:text-[2.1rem]">
                      {item.label}
                    </span>
                    <span
                      className={`ml-auto h-px w-0 bg-indigo-300/80 transition-all duration-300 group-hover:w-8 ${
                        active ? "w-8" : ""
                      }`}
                    />
                  </Link>
                );
              })}
            </nav>
          </aside>
        </div>

        <main className="relative rounded-none bg-white/[0.02] p-0 shadow-[0_20px_45px_rgba(0,0,0,0.4)] backdrop-blur-xl md:rounded-3xl md:p-2">
          {children}
        </main>
      </div>
    </div>
  );
}

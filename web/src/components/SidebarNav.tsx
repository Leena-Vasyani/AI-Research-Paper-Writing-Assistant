"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import ProjectLogo from "@/components/ProjectLogo";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/smart-drafter", label: "Smart Drafter" },
  { href: "/universal-research-formatter", label: "Universal Formatter" },
  { href: "/diagram-generator", label: "Text to Diagram" },
  { href: "/code-to-pseudocode", label: "Code to Pseudocode" },
  { href: "/workflow", label: "Workflow" },
  { href: "/agent-hub", label: "Agent Hub" },
  { href: "/about", label: "About" },
];

export default function SidebarNav() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-6 hidden h-[calc(100vh-3rem)] w-60 shrink-0 flex-col gap-4 rounded-3xl bg-zinc-900/65 p-4 shadow-[0_20px_45px_rgba(0,0,0,0.4)] backdrop-blur-xl md:flex lg:w-56">
      <div>
        <ProjectLogo variant="full" showTagline />
      </div>

      <nav className="flex flex-col gap-1.5">
        {navItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-xl border px-3 py-2 text-[15px] transition ${
                active
                  ? "border-indigo-400/45 bg-indigo-500/18 font-medium text-indigo-100"
                  : "border-zinc-800/80 text-zinc-300 hover:border-zinc-700 hover:bg-zinc-800/60 hover:text-zinc-100"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto rounded-2xl border border-zinc-800/80 bg-zinc-950/70 p-3 backdrop-blur-sm">
        <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">
          Status
        </div>
        <div className="mt-2 flex items-center gap-2 text-[13px] text-zinc-200">
          <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400" />
          Platform active
        </div>
      </div>
    </aside>
  );
}

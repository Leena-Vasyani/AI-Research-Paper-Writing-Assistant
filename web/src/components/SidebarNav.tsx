"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

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
    <aside className="hidden w-64 shrink-0 flex-col gap-6 rounded-3xl bg-zinc-900/70 p-6 shadow-lg md:flex">
      <div>
        <div className="text-lg font-semibold">ResearchGen</div>
        <p className="mt-1 text-xs text-zinc-400">
          Multi-agent research studio
        </p>
      </div>

      <nav className="flex flex-col gap-2">
        {navItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-xl px-4 py-2 text-sm transition ${
                active
                  ? "bg-indigo-500/20 text-indigo-200"
                  : "text-zinc-300 hover:bg-zinc-800/60"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto rounded-xl border border-zinc-800 bg-zinc-950/60 p-4">
        <div className="text-xs uppercase text-zinc-500">Status</div>
        <div className="mt-2 flex items-center gap-2 text-sm">
          <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400" />
          UI ready
        </div>
      </div>
    </aside>
  );
}

import type { ReactNode } from "react";
import Link from "next/link";
import SidebarNav from "@/components/SidebarNav";

const mobileNav = [
  { href: "/", label: "Home" },
  { href: "/smart-drafter", label: "Drafter" },
  { href: "/diagram-generator", label: "Diagram" },
  { href: "/workflow", label: "Workflow" },
  { href: "/about", label: "About" },
];

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-[1400px] px-4 py-4 md:px-6 md:py-6">
        <div className="mb-4 flex items-center justify-between rounded-2xl bg-zinc-900/70 px-4 py-3 md:hidden">
          <div className="text-sm font-semibold">ResearchGen</div>
          <nav className="flex items-center gap-2 text-xs text-zinc-300">
            {mobileNav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-full bg-zinc-800 px-3 py-1"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex gap-6">
          <SidebarNav />
          <main className="flex-1 rounded-3xl bg-zinc-950/60 p-0 md:p-2">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}

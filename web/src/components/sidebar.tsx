"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ArrowLeftRight,
  CheckCircle2,
  TrendingUp,
  Activity,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useAlerts } from "@/hooks/use-alerts";

const navItems = [
  { href: "/", label: "Command Center", icon: LayoutDashboard },
  { href: "/trade", label: "Trade Center", icon: ArrowLeftRight },
  { href: "/approved", label: "Approved Cards", icon: CheckCircle2 },
  { href: "/performance", label: "Alert Performance", icon: TrendingUp },
  { href: "/pulse", label: "Market Pulse", icon: Activity },
];

export function Sidebar() {
  const pathname = usePathname();
  const { alerts, pending, approved, isLoading } = useAlerts();
  const [istString, setIstString] = useState("");

  useEffect(() => {
    const fmt = () =>
      new Date().toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
        weekday: "short",
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true,
      });
    setIstString(fmt());
    const timer = setInterval(() => setIstString(fmt()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <aside className="w-64 h-screen bg-card border-r border-border flex flex-col p-4">
      {/* Brand */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center text-white font-bold text-sm shrink-0">
          J
        </div>
        <div>
          <div className="text-sm font-bold text-primary tracking-wide">
            JHAVERI
          </div>
          <div className="text-xs text-muted-foreground">
            Intelligence Platform
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <Card className="mb-6 py-3 gap-0">
        <CardContent className="px-3 py-0">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-lg font-bold">
                {isLoading ? "-" : alerts.length}
              </div>
              <div className="text-[10px] text-muted-foreground uppercase tracking-wide">
                Total
              </div>
            </div>
            <div>
              <div className="text-lg font-bold text-amber-600">
                {isLoading ? "-" : pending.length}
              </div>
              <div className="text-[10px] text-muted-foreground uppercase tracking-wide">
                Pending
              </div>
            </div>
            <div>
              <div className="text-lg font-bold text-primary">
                {isLoading ? "-" : approved.length}
              </div>
              <div className="text-[10px] text-muted-foreground uppercase tracking-wide">
                Approved
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Navigation */}
      <nav className="flex flex-col gap-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg py-2 px-3 text-sm transition-colors ${
                isActive
                  ? "bg-primary/10 text-primary font-semibold"
                  : "text-muted-foreground hover:bg-muted"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="mt-auto">
        <hr className="border-border mb-4" />
        <div className="text-xs text-muted-foreground space-y-1">
          <div>{istString || "\u00A0"}</div>
          <div className="text-[10px]">Auto-refreshing every 30s</div>
        </div>
      </div>
    </aside>
  );
}

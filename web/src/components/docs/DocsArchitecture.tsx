"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Briefcase } from "lucide-react";

export function DocsArchitecture() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Briefcase className="h-4 w-4 text-primary" />
          Technical Architecture
        </CardTitle>
      </CardHeader>
      <CardContent className="text-sm space-y-3">
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50">
                <th className="text-left px-4 py-2 font-medium text-foreground">Layer</th>
                <th className="text-left px-4 py-2 font-medium text-foreground">Technology</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground">
              <tr className="border-t border-border">
                <td className="px-4 py-2">Frontend</td>
                <td className="px-4 py-2">Next.js 16 + TypeScript + Tailwind CSS + shadcn/ui</td>
              </tr>
              <tr className="border-t border-border">
                <td className="px-4 py-2">Backend API</td>
                <td className="px-4 py-2">Python FastAPI (single server on port 8000)</td>
              </tr>
              <tr className="border-t border-border">
                <td className="px-4 py-2">Database</td>
                <td className="px-4 py-2">PostgreSQL (RDS Mumbai) / SQLite (local dev)</td>
              </tr>
              <tr className="border-t border-border">
                <td className="px-4 py-2">ORM</td>
                <td className="px-4 py-2">SQLAlchemy</td>
              </tr>
              <tr className="border-t border-border">
                <td className="px-4 py-2">Charts</td>
                <td className="px-4 py-2">Recharts (area, line, pie, gauges)</td>
              </tr>
              <tr className="border-t border-border">
                <td className="px-4 py-2">Scheduling</td>
                <td className="px-4 py-2">APScheduler (CronTrigger for daily tasks)</td>
              </tr>
              <tr className="border-t border-border">
                <td className="px-4 py-2">Deployment</td>
                <td className="px-4 py-2">AWS EC2 Mumbai (Docker via GitHub Actions CI/CD)</td>
              </tr>
              <tr className="border-t border-border">
                <td className="px-4 py-2">Market Data</td>
                <td className="px-4 py-2">nsetools (live 135+ indices) + yfinance (historical + stocks) + NSE API (sector constituents)</td>
              </tr>
              <tr className="border-t border-border">
                <td className="px-4 py-2">AI Analysis</td>
                <td className="px-4 py-2">Claude API (chart analysis, technical interpretation)</td>
              </tr>
              <tr className="border-t border-border">
                <td className="px-4 py-2">Monitoring</td>
                <td className="px-4 py-2">Sentry (error tracking, performance monitoring)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

"use client";

import { BookOpen } from "lucide-react";
import { PageInfo } from "@/components/page-info";
import { DocsOverview } from "@/components/docs/DocsOverview";
import { DocsDataSources } from "@/components/docs/DocsDataSources";
import { DocsFeatures } from "@/components/docs/DocsFeatures";
import { DocsCalculations } from "@/components/docs/DocsCalculations";
import { DocsArchitecture } from "@/components/docs/DocsArchitecture";

export default function DocsPage() {
  return (
    <div className="space-y-6 sm:space-y-8 max-w-4xl">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2">
          <BookOpen className="size-5 sm:size-6 text-primary" />
          <h1 className="text-xl sm:text-2xl font-bold text-foreground">Documentation</h1>
        </div>
        <p className="text-xs sm:text-sm text-muted-foreground mt-1">
          Complete reference for the Jhaveri Intelligence Platform
        </p>
      </div>

      <PageInfo>
        Platform reference covering the alert system, sentiment engine, portfolio calculations,
        recommendation methodology, and technical architecture. Updated for the v3 platform
        with streamlined 2-page alert flow, per-stock sentiment scoring, and 48 sector/thematic indices.
      </PageInfo>

      <DocsOverview />
      <DocsDataSources />
      <DocsFeatures />
      <DocsCalculations />
      <DocsArchitecture />

      {/* Footer */}
      <div className="text-xs text-muted-foreground pb-8">
        <p>Jhaveri Intelligence Platform v3 &mdash; Built for Jhaveri Securities & Ventures</p>
      </div>
    </div>
  );
}

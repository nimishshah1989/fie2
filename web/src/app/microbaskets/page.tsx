"use client";

import { useState } from "react";
import { useBasketsLive } from "@/hooks/use-baskets";
import { BasketRichCard } from "@/components/basket/basket-rich-card";
import { BasketDetailPanel } from "@/components/basket/basket-detail-panel";
import { CreateBasketDialog } from "@/components/basket/create-basket-dialog";
import { CsvUploadDialog } from "@/components/basket/csv-upload-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BASE_INDEX_OPTIONS, PERIOD_OPTIONS } from "@/lib/constants";
import { formatTimestamp } from "@/lib/utils";
import { Layers, Plus, Upload } from "lucide-react";
import type { BasketLiveItem } from "@/lib/basket-types";
import { PageInfo } from "@/components/page-info";

export default function MicrobasketsPage() {
  const [base, setBase] = useState("NIFTY");
  const [period, setPeriod] = useState("1M");
  const [selectedBasketId, setSelectedBasketId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [csvOpen, setCsvOpen] = useState(false);
  const [editBasket, setEditBasket] = useState<BasketLiveItem | null>(null);

  const { data, error, isLoading, mutate } = useBasketsLive(base);

  const selectedBasket = data.baskets.find((b) => b.id === selectedBasketId) ?? null;

  function handleSelect(id: number) {
    setSelectedBasketId(selectedBasketId === id ? null : id);
  }

  function handleEdit(basket: BasketLiveItem) {
    setEditBasket(basket);
    setCreateOpen(true);
  }

  function handleCreateSuccess() {
    mutate();
    setEditBasket(null);
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Layers className="size-5 sm:size-6 text-blue-600" />
          <h1 className="text-xl sm:text-2xl font-bold text-foreground">Microbaskets</h1>
        </div>
        <p className="text-xs sm:text-sm text-muted-foreground mt-1">
          Custom stock baskets with ratio analysis vs benchmark indices
        </p>
      </div>

      <PageInfo>
        Custom stock baskets with ratio analysis versus a benchmark index. Create baskets manually or upload via CSV.
        Each basket tracks NAV history, constituent-level performance, and relative returns.
        Set a portfolio size to calculate optimal unit allocation per constituent.
      </PageInfo>

      {/* Action Bar */}
      <div className="grid grid-cols-2 sm:flex sm:flex-wrap sm:items-center gap-2 sm:gap-3">
        {/* Base Index */}
        <Select value={base} onValueChange={setBase}>
          <SelectTrigger className="w-full sm:w-[160px]">
            <SelectValue placeholder="Base Index" />
          </SelectTrigger>
          <SelectContent>
            {BASE_INDEX_OPTIONS.map((opt) => (
              <SelectItem key={opt} value={opt}>{opt}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Period */}
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-full sm:w-[100px]">
            <SelectValue placeholder="Period" />
          </SelectTrigger>
          <SelectContent>
            {PERIOD_OPTIONS.map((opt) => (
              <SelectItem key={opt} value={opt}>{opt}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Spacer on desktop */}
        <div className="hidden sm:block sm:flex-1" />

        {/* Action buttons */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setCsvOpen(true)}
          className="col-span-1"
        >
          <Upload className="h-4 w-4 mr-1.5" />
          Upload CSV
        </Button>
        <Button
          size="sm"
          onClick={() => { setEditBasket(null); setCreateOpen(true); }}
          className="col-span-1"
        >
          <Plus className="h-4 w-4 mr-1.5" />
          Create Basket
        </Button>
      </div>

      {/* Info Caption */}
      {!isLoading && data.baskets.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {data.baskets.length} basket{data.baskets.length !== 1 ? "s" : ""}
          {" "}&bull;{" "}
          Last refreshed {formatTimestamp(data.timestamp)}
        </p>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load basket data. Please try again later.
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-[300px] rounded-xl" />
        </div>
      )}

      {/* Content */}
      {!isLoading && !error && data.baskets.length > 0 && (
        <>
          {/* Basket Rich Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.baskets.map((basket) => (
              <BasketRichCard
                key={basket.id}
                basket={basket}
                period={period}
                isSelected={selectedBasketId === basket.id}
                onClick={() => handleSelect(basket.id)}
              />
            ))}
          </div>

          {/* Detail Panel */}
          {selectedBasket && (
            <>
              <hr className="border-border" />
              <BasketDetailPanel
                basket={selectedBasket}
                onClose={() => setSelectedBasketId(null)}
                onEdit={handleEdit}
                onMutate={() => mutate()}
              />
            </>
          )}
        </>
      )}

      {/* Empty State */}
      {!isLoading && !error && data.baskets.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Layers className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-lg font-semibold text-foreground">No microbaskets yet</h3>
          <p className="text-sm text-muted-foreground mt-1 max-w-sm">
            Create custom stock baskets to track niche sectors with ratio analysis against benchmark indices.
          </p>
          <div className="flex gap-2 mt-4">
            <Button variant="outline" size="sm" onClick={() => setCsvOpen(true)}>
              <Upload className="h-4 w-4 mr-1.5" />
              Upload CSV
            </Button>
            <Button size="sm" onClick={() => { setEditBasket(null); setCreateOpen(true); }}>
              <Plus className="h-4 w-4 mr-1.5" />
              Create First Basket
            </Button>
          </div>
        </div>
      )}

      {/* Dialogs */}
      <CreateBasketDialog
        open={createOpen}
        onOpenChange={(open) => { setCreateOpen(open); if (!open) setEditBasket(null); }}
        onSuccess={handleCreateSuccess}
        editBasket={editBasket}
      />
      <CsvUploadDialog
        open={csvOpen}
        onOpenChange={setCsvOpen}
        onSuccess={() => mutate()}
      />
    </div>
  );
}

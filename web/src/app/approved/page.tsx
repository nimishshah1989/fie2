"use client";

import { useState, useMemo, useCallback } from "react";
import { CheckCircle2, Search } from "lucide-react";
import { useAlerts } from "@/hooks/use-alerts";
import type { Alert } from "@/lib/types";
import { deleteAlert } from "@/lib/api";
import { StatsRow } from "@/components/stats-row";
import { ApprovedCard } from "@/components/approved-card";
import { DetailPanel } from "@/components/detail-panel";
import { FmActionDialog } from "@/components/fm-action-dialog";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
} from "@/components/ui/sheet";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type UrgencyFilter = "all" | "IMMEDIATELY" | "WITHIN_A_WEEK" | "WITHIN_A_MONTH";
type SignalFilter = "all" | "BULLISH" | "BEARISH";

export default function ApprovedPage() {
  const { approved, isLoading, mutate } = useAlerts();

  const [urgencyFilter, setUrgencyFilter] = useState<UrgencyFilter>("all");
  const [signalFilter, setSignalFilter] = useState<SignalFilter>("all");
  const [search, setSearch] = useState("");
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  // Edit dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editAlert, setEditAlert] = useState<Alert | null>(null);

  // Delete confirmation state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Alert | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Count urgency categories
  const immediatelyCount = useMemo(
    () => approved.filter((a) => a.action?.priority === "IMMEDIATELY").length,
    [approved]
  );
  const withinWeekCount = useMemo(
    () => approved.filter((a) => a.action?.priority === "WITHIN_A_WEEK").length,
    [approved]
  );
  const withinMonthCount = useMemo(
    () => approved.filter((a) => a.action?.priority === "WITHIN_A_MONTH").length,
    [approved]
  );

  // Filter approved alerts
  const filteredAlerts = useMemo(() => {
    let result = approved;

    if (urgencyFilter !== "all") {
      result = result.filter((a) => a.action?.priority === urgencyFilter);
    }

    if (signalFilter !== "all") {
      result = result.filter((a) => a.signal_direction === signalFilter);
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter((a) => a.ticker.toLowerCase().includes(q));
    }

    return result;
  }, [approved, urgencyFilter, signalFilter, search]);

  const sheetOpen = selectedAlert !== null;

  function handleCardClick(alert: Alert) {
    if (selectedAlert?.id === alert.id) {
      setSelectedAlert(null);
    } else {
      setSelectedAlert(alert);
    }
  }

  const handleEdit = useCallback(() => {
    if (!selectedAlert) return;
    setEditAlert(selectedAlert);
    setEditDialogOpen(true);
  }, [selectedAlert]);

  const handleEditSubmitted = useCallback(() => {
    setEditDialogOpen(false);
    setEditAlert(null);
    mutate(); // Refresh data
    // Re-select to get fresh data
    setSelectedAlert(null);
  }, [mutate]);

  const handleDeleteRequest = useCallback(() => {
    if (!selectedAlert) return;
    setDeleteTarget(selectedAlert);
    setDeleteDialogOpen(true);
  }, [selectedAlert]);

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const result = await deleteAlert(deleteTarget.id);
      if (result.success) {
        setDeleteDialogOpen(false);
        setDeleteTarget(null);
        setSelectedAlert(null);
        mutate(); // Refresh data
      }
    } catch {
      // ignore
    } finally {
      setDeleting(false);
    }
  }, [deleteTarget, mutate]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Approved Cards</h1>
        <p className="text-sm text-muted-foreground mt-1">
          FM-approved alerts with action recommendations
        </p>
      </div>

      {/* Stats Row */}
      <StatsRow
        stats={[
          {
            label: "Total Approved",
            value: isLoading ? "-" : approved.length,
          },
          {
            label: "Immediately",
            value: isLoading ? "-" : immediatelyCount,
            color: "text-orange-600",
          },
          {
            label: "Within a Week",
            value: isLoading ? "-" : withinWeekCount,
            color: "text-blue-600",
          },
          {
            label: "Within a Month",
            value: isLoading ? "-" : withinMonthCount,
            color: "text-purple-600",
          },
        ]}
      />

      {/* Filters Row */}
      <div className="flex flex-wrap items-center gap-3">
        <Select
          value={urgencyFilter}
          onValueChange={(v) => setUrgencyFilter(v as UrgencyFilter)}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Urgency" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Urgencies</SelectItem>
            <SelectItem value="IMMEDIATELY">Immediately</SelectItem>
            <SelectItem value="WITHIN_A_WEEK">Within a Week</SelectItem>
            <SelectItem value="WITHIN_A_MONTH">Within a Month</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={signalFilter}
          onValueChange={(v) => setSignalFilter(v as SignalFilter)}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Signal" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Signals</SelectItem>
            <SelectItem value="BULLISH">Bullish</SelectItem>
            <SelectItem value="BEARISH">Bearish</SelectItem>
          </SelectContent>
        </Select>

        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by ticker..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Card Grid / Loading / Empty */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      ) : filteredAlerts.length === 0 ? (
        <EmptyState
          icon={<CheckCircle2 className="h-12 w-12" />}
          title="No approved alerts"
          description={
            search || urgencyFilter !== "all" || signalFilter !== "all"
              ? "Try adjusting your filters or search term."
              : "Approved alerts will appear here once the FM takes action."
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredAlerts.map((alert) => (
            <ApprovedCard
              key={alert.id}
              alert={alert}
              onClick={() => handleCardClick(alert)}
              isSelected={selectedAlert?.id === alert.id}
            />
          ))}
        </div>
      )}

      {/* Detail Sheet (right drawer) */}
      <Sheet open={sheetOpen} onOpenChange={(open) => { if (!open) setSelectedAlert(null); }}>
        <SheetContent className="w-full sm:max-w-xl overflow-y-auto p-0">
          {selectedAlert && (
            <div className="p-6">
              <DetailPanel
                alert={selectedAlert}
                onClose={() => setSelectedAlert(null)}
                onEdit={handleEdit}
                onDelete={handleDeleteRequest}
              />
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Edit Dialog */}
      <FmActionDialog
        alert={editAlert}
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        onSubmitted={handleEditSubmitted}
        mode="edit"
        initialData={editAlert?.action ?? null}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Delete Alert</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the alert for{" "}
              <span className="font-semibold text-foreground">
                {deleteTarget?.ticker}
              </span>
              ? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center justify-end gap-3 pt-4">
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleting}
            >
              {deleting ? "Deleting..." : "Delete"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

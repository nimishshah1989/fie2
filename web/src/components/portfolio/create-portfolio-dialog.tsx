"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { createPortfolio } from "@/lib/portfolio-api";
import { Plus } from "lucide-react";

const BENCHMARK_OPTIONS = [
  "NIFTY",
  "SENSEX",
  "BANKNIFTY",
  "NIFTYIT",
  "NIFTYPHARMA",
  "NIFTYFMCG",
  "NIFTYAUTO",
  "NIFTYMETAL",
];

interface CreatePortfolioDialogProps {
  onCreated: () => void;
}

export function CreatePortfolioDialog({ onCreated }: CreatePortfolioDialogProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [benchmark, setBenchmark] = useState("NIFTY");
  const [loading, setLoading] = useState(false);

  async function handleCreate() {
    if (!name.trim()) return;
    setLoading(true);
    try {
      const result = await createPortfolio({
        name: name.trim(),
        description: description.trim() || undefined,
        benchmark,
      });
      if (result.success) {
        setOpen(false);
        setName("");
        setDescription("");
        setBenchmark("NIFTY");
        onCreated();
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1.5">
          <Plus className="h-4 w-4" />
          Create Portfolio
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create Model Portfolio</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <Label htmlFor="name">Strategy Name</Label>
            <Input
              id="name"
              placeholder="e.g. Large Cap Growth"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Brief description of the investment strategy..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          <div className="space-y-1.5">
            <Label>Benchmark Index</Label>
            <Select value={benchmark} onValueChange={setBenchmark}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {BENCHMARK_OPTIONS.map((b) => (
                  <SelectItem key={b} value={b}>
                    {b}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button
            className="w-full"
            onClick={handleCreate}
            disabled={!name.trim() || loading}
          >
            {loading ? "Creating..." : "Create Portfolio"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

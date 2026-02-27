import { formatPrice, formatVolume } from "@/lib/utils";

interface OhlcvStripProps {
  open: number | null | undefined;
  high: number | null | undefined;
  low: number | null | undefined;
  close: number | null | undefined;
  volume: number | null | undefined;
}

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
        {label}
      </span>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  );
}

export function OhlcvStrip({ open, high, low, close, volume }: OhlcvStripProps) {
  return (
    <div className="flex items-center gap-4 bg-muted/50 rounded-lg px-3 py-2">
      <Item label="Open" value={formatPrice(open)} />
      <Item label="High" value={formatPrice(high)} />
      <Item label="Low" value={formatPrice(low)} />
      <Item label="Close" value={formatPrice(close)} />
      <Item label="Volume" value={formatVolume(volume)} />
    </div>
  );
}

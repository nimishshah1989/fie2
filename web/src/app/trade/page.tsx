"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function TradeRedirectPage() {
  const router = useRouter();
  useEffect(() => { router.replace("/"); }, [router]);
  return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <p className="text-sm text-slate-500">Redirecting...</p>
    </div>
  );
}

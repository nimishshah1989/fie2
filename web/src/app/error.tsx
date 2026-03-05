"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
      <h2 className="text-lg font-semibold text-red-600">Something went wrong</h2>
      <pre className="text-xs text-muted-foreground bg-muted p-4 rounded-lg max-w-xl overflow-auto whitespace-pre-wrap">
        {error.message}
      </pre>
      {error.stack && (
        <details className="text-xs text-muted-foreground max-w-xl">
          <summary className="cursor-pointer">Stack trace</summary>
          <pre className="bg-muted p-3 rounded-lg mt-2 overflow-auto whitespace-pre-wrap">
            {error.stack}
          </pre>
        </details>
      )}
      <button
        onClick={() => reset()}
        className="px-4 py-2 bg-teal-600 text-white rounded-lg text-sm hover:bg-teal-700"
      >
        Try again
      </button>
    </div>
  );
}

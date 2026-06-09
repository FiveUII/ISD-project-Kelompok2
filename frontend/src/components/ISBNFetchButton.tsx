/**
 * ISBNFetchButton — fetches book metadata from Open Library via POST /api/books/isbn-fetch.
 * Shows inline Alert below the button with exact copywriting per UI-SPEC.
 * Does NOT use browser alert() — renders shadcn Alert component.
 */
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { apiClient } from "@/lib/api";

export interface ISBNFetchResult {
  found: boolean;
  title?: string;
  author?: string;
  description?: string;
  cover_url?: string;
  error?: string;
}

type FetchStatus = "idle" | "loading" | "success" | "not_found" | "unavailable";

interface ISBNFetchButtonProps {
  isbn: string;
  onResult: (result: ISBNFetchResult) => void;
}

export default function ISBNFetchButton({ isbn, onResult }: ISBNFetchButtonProps) {
  const [status, setStatus] = useState<FetchStatus>("idle");

  const handleFetch = async () => {
    setStatus("loading");
    try {
      const response = await apiClient.post<ISBNFetchResult>("/books/isbn-fetch", { isbn });
      const data = response.data;
      if (data.found) {
        onResult(data);
        setStatus("success");
      } else if (data.error === "not_found") {
        setStatus("not_found");
      } else {
        setStatus("unavailable");
      }
    } catch {
      setStatus("unavailable");
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <Button
        type="button"
        onClick={handleFetch}
        disabled={status === "loading"}
        className="bg-blue-600 text-white hover:bg-blue-700"
      >
        {status === "loading" ? "Fetching..." : "Fetch Details"}
      </Button>

      {status === "success" && (
        <Alert variant="default">
          <AlertDescription>
            Details filled from Open Library. Review and save.
          </AlertDescription>
        </Alert>
      )}
      {status === "not_found" && (
        <Alert variant="default">
          <AlertDescription>
            No book found for this ISBN. Fill in the details manually.
          </AlertDescription>
        </Alert>
      )}
      {status === "unavailable" && (
        <Alert variant="destructive">
          <AlertDescription>
            Service unavailable — fill in the details manually.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

# Phase 2: Catalog - Research

**Researched:** 2026-06-09
**Domain:** Book catalog CRUD, Open Library API integration, SQLAlchemy async search queries, shadcn/ui DataTable, TanStack Query v5 mutations, Alembic index migration, URL-driven search
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Unknown ISBN — show inline error "No book found for this ISBN", keep librarian on form, allow manual fill.
- D-02: Unreachable Open Library (timeout/5xx) — show inline error "Service unavailable — please fill in details manually". No retry. Same pattern as D-01.
- D-03: Auto-fill ONLY title, author, description from Open Library. publisher and publish_year NOT auto-filled.
- D-04: PostgreSQL ILIKE substring search across title OR author OR ISBN. No pg_trgm. Single `q` param.
- D-05: Offset-based pagination: 20 per page, `?q=&page=1&page_size=20`.
- D-06: Soft-deleted books excluded from ALL search results (students and librarians). `deleted_at IS NULL` universal filter. No "show deleted" view in Phase 2.
- D-07: Routes: `/catalog` (student), `/librarian/books` (list), `/librarian/books/new` (add), `/librarian/books/:id` (detail + copies).
- D-08: Copies managed inline on book detail page. No separate `/copies` route.
- D-09: Librarian book list: shadcn/ui DataTable with sortable columns (title, author, ISBN, available copies, total copies). Row actions: Edit, Delete (soft-delete).
- D-10: Phase 2 introduces shared layout shell. Auth pages stay outside. Authenticated pages wrapped in shell. Nav: student sees "Catalog"; librarian sees "Catalog" + "Manage Books".
- D-11: Students see only available copy count (e.g., "3 available"). NOT "3 of 5".
- D-12: Available copy count included in book list API response via SQL subquery — no separate endpoint, no N+1.

### Claude's Discretion
- Open Library API timeout: 5 seconds.
- `/catalog` requires authentication (not public). Unauthenticated users redirect to `/login`.
- Librarians can also use `/catalog`.
- Copies section on book detail: show each copy's full status (available/on_loan/lost) and barcode. Soft-deleted copies hidden.

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

---

## Summary

Phase 2 has six research domains. All six have clear, verified implementation paths with no blocking unknowns, but three have gotchas that will cause bugs if missed.

**Gotcha 1 — Open Library description field:** The description on the Works record is NOT always a plain string. It is frequently an object `{"type": "/type/text", "value": "..."}`. Code that does `description = works_data.get("description")` will store the entire dict as a string if not handled. Must extract `description["value"]` when it's a dict.

**Gotcha 2 — Open Library author name:** The `/isbn/{isbn}.json` edition endpoint does NOT embed author names — `authors` is `[{"key": "/authors/OL34184A"}]`. Getting the author name requires a second HTTP call to `/authors/{key}.json` to fetch the `name` field. Since D-03 says auto-fill only title/author/description, the fetch sequence is: edition → works (for description) → author (for name) — up to 3 sequential HTTPX calls.

**Gotcha 3 — shadcn/ui requires `@/*` path alias:** shadcn components use `@/components/ui/...` imports. The current `tsconfig.json` and `vite.config.ts` do NOT have this alias configured. Must add it before `npx shadcn@latest init` or all component imports break.

**Primary recommendation:** Implement Open Library fetch as a 3-step coroutine (edition → works → author) with explicit `description` type-check; wire shadcn DataTable using verified patterns below; use `[queryKey: ['books', {q, page}]]` pattern for URL-driven re-fetching.

---

## Open Library API

### Endpoint Structure

**Edition endpoint (Step 1):**
```
GET https://openlibrary.org/isbn/{isbn}.json
```

**Response fields for a known ISBN:**

| Field | Type | Notes |
|-------|------|-------|
| `title` | string | Present on most edition records |
| `authors` | array | `[{"key": "/authors/OL34184A"}]` — key reference only, NO inline name |
| `by_statement` | string | Sometimes present (e.g., "by Kurt Vonnegut") but unreliable; do NOT use as author name |
| `works` | array | `[{"key": "/works/OL45804W"}]` — needed to fetch description |
| `description` | string or object or absent | Rare on edition records; usually lives on the works record |
| `publishers` | array of strings | Available but D-03 says do NOT auto-fill publisher |
| `publish_date` | string | Available but D-03 says do NOT auto-fill |
| `covers` | array of int IDs | Cover image IDs (cover URL pattern below) |

**404 response:** HTTP 404 with no JSON body. HTTPX `response.status_code == 404` is the check. There is no JSON error envelope — do not attempt `response.json()` on a 404.

**Author endpoint (Step 2 — required for author name):**
```
GET https://openlibrary.org/authors/{author_key}.json
```
Returns `{"name": "Roald Dahl", "personal_name": ..., ...}`. The `name` field is the display name to use.

**Works endpoint (Step 3 — required for description):**
```
GET https://openlibrary.org/works/{works_key}.json
```

**CRITICAL: description field is polymorphic.**
- Sometimes absent (field does not exist on the works record)
- Sometimes a plain string: `"description": "A story about..."`
- Sometimes an object: `"description": {"type": "/type/text", "value": "A story about..."}`

[VERIFIED: direct API call to openlibrary.org/works/OL82537W.json] — confirmed object format.
[VERIFIED: direct API call to openlibrary.org/works/OL7353617W.json] — confirmed absent case.

**Normalization function required:**
```python
def _extract_description(raw) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw or None
    if isinstance(raw, dict):
        return raw.get("value") or None
    return None
```

**Cover URL pattern:**
```
https://covers.openlibrary.org/b/id/{cover_id}-M.jpg
```
(M = medium; L = large; S = small). Available if `covers` array is non-empty.

### Fetch Sequence (implementation pattern)

```python
import httpx
from typing import Optional

OPEN_LIBRARY_TIMEOUT = 5.0  # seconds (Claude's Discretion)
OL_BASE = "https://openlibrary.org"

async def fetch_isbn_metadata(isbn: str) -> Optional[dict]:
    """
    Returns dict with keys: title, author, description (all Optional[str]).
    Returns None if ISBN not found (404).
    Raises httpx.TimeoutException on timeout (D-02 path: treat as unreachable).
    Raises httpx.HTTPStatusError on 5xx (D-02 path: treat as unreachable).
    """
    async with httpx.AsyncClient(timeout=OPEN_LIBRARY_TIMEOUT) as client:
        # Step 1: Edition
        resp = await client.get(f"{OL_BASE}/isbn/{isbn}.json",
                                headers={"User-Agent": "LibraryManagementSystem (contact@example.org)"})
        if resp.status_code == 404:
            return None  # D-01: ISBN not found
        resp.raise_for_status()  # D-02: 5xx → caller shows "Service unavailable"
        edition = resp.json()

        title: str | None = edition.get("title")

        # Step 2: Author (requires separate fetch — name is NOT in edition)
        author: str | None = None
        authors_list = edition.get("authors", [])
        if authors_list:
            author_key = authors_list[0].get("key", "")  # e.g. "/authors/OL34184A"
            if author_key:
                author_resp = await client.get(f"{OL_BASE}{author_key}.json",
                                               headers={"User-Agent": "LibraryManagementSystem (contact@example.org)"})
                if author_resp.status_code == 200:
                    author = author_resp.json().get("name")

        # Step 3: Works (for description)
        description: str | None = None
        works_list = edition.get("works", [])
        if works_list:
            works_key = works_list[0].get("key", "")  # e.g. "/works/OL45804W"
            if works_key:
                works_resp = await client.get(f"{OL_BASE}{works_key}.json",
                                              headers={"User-Agent": "LibraryManagementSystem (contact@example.org)"})
                if works_resp.status_code == 200:
                    raw_desc = works_resp.json().get("description")
                    description = _extract_description(raw_desc)

        return {"title": title, "author": author, "description": description}
```

### Rate Limits

[CITED: openlibrary.org/developers/api] — 1 req/sec for anonymous, 3 req/sec with `User-Agent` header including app name + contact email. Always include the User-Agent header. This is per-IP and applies to all endpoints.

**Implication for this phase:** The ISBN fetch sequence makes up to 3 sequential calls (edition → author → works). At 5s timeout each, worst-case is 15s. With User-Agent header and typical response times (~200ms each), real-world is ~600ms. No retry logic needed (D-02). Cache responses if the same ISBN is fetched repeatedly.

### What to Do With Each Field (D-03 compliance)

| Open Library field | Destination | Notes |
|--------------------|-------------|-------|
| `title` | `BookCreate.title` | Auto-fill |
| `author` (from `/authors/`) | `BookCreate.author` | Auto-fill |
| `description` (from `/works/`) | `BookCreate.description` | Auto-fill; extract `.value` if dict |
| `publishers[0]` | DO NOT auto-fill | D-03: publisher excluded |
| `publish_date` | DO NOT auto-fill | D-03: publish_year excluded |
| `covers[0]` via URL template | `BookCreate.cover_url` | Not mentioned in D-03 scope but reasonable to include — planner decision |

---

## SQLAlchemy 2.0 Async: Availability Subquery + ILIKE Search

### Pattern 1: Correlated Scalar Subquery for Available Copy Count

This is the pattern for D-12 (no N+1, count inline in book list query).

```python
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.book import Book
from app.models.copy import Copy
from app.core.enums import CopyStatus

# Correlated subquery: count of available, non-deleted copies per book
available_count_subq = (
    select(func.count(Copy.id))
    .where(
        and_(
            Copy.book_id == Book.id,         # correlation to outer query
            Copy.status == CopyStatus.available,
            Copy.deleted_at.is_(None),
        )
    )
    .correlate(Book)                          # explicit correlation
    .scalar_subquery()
    .label("available_count")
)
```

[VERIFIED: docs.sqlalchemy.org/en/20/tutorial/data_select.html] — `select(...).scalar_subquery()` is the documented method on `Select`. `.correlate(Book)` makes it correlated. `func.count()` from `sqlalchemy` is the aggregate.

**Full book list query with search + pagination:**

```python
async def list_books(
    session: AsyncSession,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple], int]:
    """Returns (rows, total_count)."""

    available_count_subq = (
        select(func.count(Copy.id))
        .where(
            and_(
                Copy.book_id == Book.id,
                Copy.status == CopyStatus.available,
                Copy.deleted_at.is_(None),
            )
        )
        .correlate(Book)
        .scalar_subquery()
    )

    # Base filter: exclude soft-deleted (D-06)
    base_where = [Book.deleted_at.is_(None)]

    # ILIKE search across 3 columns (D-04)
    if q:
        pattern = f"%{q}%"
        base_where.append(
            or_(
                Book.title.ilike(pattern),
                Book.author.ilike(pattern),
                Book.isbn.ilike(pattern),
            )
        )

    # Total count query
    count_stmt = (
        select(func.count(Book.id))
        .where(*base_where)
    )
    total = await session.scalar(count_stmt) or 0

    # Data query with availability subquery
    stmt = (
        select(Book, available_count_subq)
        .where(*base_where)
        .order_by(Book.title)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    rows = result.all()  # list of (Book, available_count) tuples

    return rows, total
```

**Key imports:**
```python
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
```

### Pattern 2: ILIKE Across Multiple Columns

`Column.ilike()` is a standard SQLAlchemy column operator — no extra import needed beyond the model class.

```python
# Case-insensitive substring match
Book.title.ilike(f"%{q}%")       # generates: books.title ILIKE '%search%'
Book.author.ilike(f"%{q}%")
Book.isbn.ilike(f"%{q}%")

# Combined with OR
or_(
    Book.title.ilike(pattern),
    Book.author.ilike(pattern),
    Book.isbn.ilike(pattern),
)
```

[CITED: docs.sqlalchemy.org/en/20/ — `ilike()` is a `ColumnOperators` method available on all mapped columns]

### Pattern 3: Offset Pagination

```python
stmt = select(Book).offset((page - 1) * page_size).limit(page_size)
```

`.offset()` and `.limit()` are methods on `Select`. Both accept integers.

### Accessing Subquery Result in Row

When `select(Book, subq)` is used, `session.execute()` returns rows of `(Book_instance, scalar_value)`:

```python
rows = result.all()
for book, available_count in rows:
    print(book.title, available_count)
```

### Total Copy Count (for librarian view)

For the librarian list (D-09 shows "total copies" column), add a second correlated subquery:

```python
total_count_subq = (
    select(func.count(Copy.id))
    .where(
        and_(
            Copy.book_id == Book.id,
            Copy.deleted_at.is_(None),
        )
    )
    .correlate(Book)
    .scalar_subquery()
    .label("total_count")
)

stmt = select(Book, available_count_subq, total_count_subq).where(...)
# Result rows: (Book, available_count, total_count)
```

---

## shadcn/ui DataTable (TanStack Table v8)

### Pre-requisite: shadcn/ui Setup (BLOCKING if not done first)

The current frontend has NO `components.json` — shadcn/ui has not been initialized. This MUST be done in Wave 0 of Phase 2 before any component can be installed.

**Step 1: Configure path alias (required by shadcn)**

`vite.config.ts` — add resolve alias:
```typescript
import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // ... existing server config
})
```

`tsconfig.json` — add to `compilerOptions`:
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
    // ... existing options
  }
}
```

Also need `@types/node` devDependency for `path.resolve`:
```bash
npm install -D @types/node
```

**Step 2: Initialize shadcn**
```bash
npx shadcn@latest init
```
This creates `components.json` and installs `tailwindcss`, `class-variance-authority`, `clsx`, `tailwind-merge` (peer deps already may be present).

**Step 3: Install components**
```bash
npx shadcn@latest add table
npx shadcn@latest add button
npx shadcn@latest add dropdown-menu
npx shadcn@latest add dialog
npx shadcn@latest add input
npx shadcn@latest add form
npx shadcn@latest add badge
```

**Step 4: Install TanStack Table**
```bash
npm install @tanstack/react-table
```

[VERIFIED: ui.shadcn.com/docs/installation/vite and ui.shadcn.com/docs/components/data-table]

### Column Definitions Pattern

```typescript
// frontend/src/features/librarian/books/columns.tsx
import { ColumnDef } from "@tanstack/react-table"
import { MoreHorizontal, ArrowUpDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export type BookRow = {
  id: number
  isbn: string | null
  title: string
  author: string
  available_count: number
  total_count: number
}

export const columns: ColumnDef<BookRow>[] = [
  {
    accessorKey: "title",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      >
        Title
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
  {
    accessorKey: "author",
    header: ({ column }) => (
      <Button variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      >
        Author <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
  {
    accessorKey: "isbn",
    header: "ISBN",
  },
  {
    accessorKey: "available_count",
    header: "Available",
  },
  {
    accessorKey: "total_count",
    header: "Total Copies",
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const book = row.original
      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <span className="sr-only">Open menu</span>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuItem onClick={() => navigate(`/librarian/books/${book.id}`)}>
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-red-600"
              onClick={() => onDelete(book.id)}
            >
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
    },
  },
]
```

### DataTable Component (with sorting)

```typescript
// frontend/src/components/ui/data-table.tsx
import React from "react"
import {
  ColumnDef,
  SortingState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
}

export function DataTable<TData, TValue>({
  columns,
  data,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([])

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    state: { sorting },
  })

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows?.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center">
                No results.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}
```

[VERIFIED: ui.shadcn.com/docs/components/data-table and ui.shadcn.com/docs/components/data-table#row-actions]

**Note:** Sorting here is client-side (TanStack Table state). For the librarian book list this is acceptable — the dataset is paginated to 20 rows. Server-side sorting is NOT needed for Phase 2.

### Important: shadcn/ui is NOT an npm package

shadcn/ui copies component source files into `src/components/ui/`. Running `npx shadcn@latest add table` copies:
- `src/components/ui/table.tsx`

Running `npx shadcn@latest add dropdown-menu` copies:
- `src/components/ui/dropdown-menu.tsx`

These are YOUR files — edit them freely. The package `@shadcn/ui` does not exist on npm. Only `shadcn` (the CLI) and peer deps (`@radix-ui/*`, `lucide-react`, `clsx`, `tailwind-merge`, `class-variance-authority`) are installed as npm packages.

---

## TanStack Query v5 — Mutations + Invalidation

### v5 API Shape (confirmed)

[VERIFIED: tanstack.com/query/v5/docs/framework/react/guides/mutations and tanstack.com/query/v5/docs/framework/react/guides/query-invalidation]

**useMutation options (v5):**
```typescript
import { useMutation, useQueryClient } from "@tanstack/react-query"

const queryClient = useQueryClient()

const createBookMutation = useMutation({
  mutationFn: (data: BookCreate) =>
    apiClient.post("/books", data).then(r => r.data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["books"] })
  },
  onError: (error) => {
    // handle error
  },
})

// Call site:
createBookMutation.mutate(formData)
// or:
await createBookMutation.mutateAsync(formData)
```

**Key v4 → v5 differences:**
- `cacheTime` renamed to `gcTime`
- `onSuccess(data, variables, context)` — same callback but `context` now has stricter typing
- `isLoading` on `useMutation` renamed to `isPending` (v5)
- `status === "loading"` → `status === "pending"` (v5)

**Checking mutation state:**
```typescript
const { mutate, isPending, isError, error } = useMutation({ ... })
// v4: isLoading — WRONG in v5
// v5: isPending — CORRECT
```

### Invalidation Pattern

```typescript
// Invalidate all queries with key starting with "books" (prefix match)
queryClient.invalidateQueries({ queryKey: ["books"] })

// Invalidate exact query only
queryClient.invalidateQueries({ queryKey: ["books", { q: "", page: 1 }], exact: true })

// After successful delete — invalidate the list and the specific book
onSuccess: (_, bookId) => {
  queryClient.invalidateQueries({ queryKey: ["books"] })
  queryClient.removeQueries({ queryKey: ["book", bookId] })
}
```

### Query Key Convention for Catalog

```typescript
// Book list (student and librarian share same cache)
["books", { q: searchQuery, page: currentPage, page_size: 20 }]

// Single book detail
["book", bookId]

// Copies for a book
["book", bookId, "copies"]
```

When `q` or `page` changes in the URL, the queryKey changes → TanStack Query automatically triggers a new fetch.

### useQuery Pattern for Book List

```typescript
const { data, isLoading, isError } = useQuery({
  queryKey: ["books", { q, page, page_size: 20 }],
  queryFn: () =>
    apiClient
      .get("/books", { params: { q, page, page_size: 20 } })
      .then(r => r.data),
  placeholderData: keepPreviousData,  // v5: show previous page while loading next
})
```

`keepPreviousData` in v5 is an import from `@tanstack/react-query` used in the `placeholderData` option (NOT the `keepPreviousData: true` boolean from v4):
```typescript
import { useQuery, keepPreviousData } from "@tanstack/react-query"
```

---

## URL-Driven Search + Pagination

### Pattern: useSearchParams → queryKey → TanStack Query

React Router v6 `useSearchParams` hook reads and writes `?q=&page=`. Passing those values into the TanStack Query `queryKey` makes URL changes automatically trigger refetches. Back/forward navigation restores the correct search state.

[CITED: tanstack.com/query/v5/docs/framework/react/reference/useQuery — "The query will automatically update when this key changes"]

```typescript
import { useSearchParams } from "react-router-dom"
import { useQuery, keepPreviousData } from "@tanstack/react-query"
import { apiClient } from "@/lib/api"

export function useCatalogSearch() {
  const [searchParams, setSearchParams] = useSearchParams()

  const q = searchParams.get("q") ?? ""
  const page = Number(searchParams.get("page") ?? "1")
  const pageSize = 20

  const { data, isLoading, isError } = useQuery({
    queryKey: ["books", { q, page, page_size: pageSize }],
    queryFn: () =>
      apiClient
        .get("/books", { params: { q: q || undefined, page, page_size: pageSize } })
        .then(r => r.data),
    placeholderData: keepPreviousData,
  })

  const setSearch = (newQ: string) => {
    setSearchParams({ q: newQ, page: "1" })  // reset to page 1 on new search
  }

  const setPage = (newPage: number) => {
    setSearchParams({ q, page: String(newPage) })
  }

  return { data, isLoading, isError, q, page, setSearch, setPage }
}
```

### setSearchParams Behavior

`setSearchParams(newParams)` REPLACES all current params. To preserve existing params while updating one:

```typescript
// Replace all (safe for 2 known params):
setSearchParams({ q: newQ, page: "1" })

// Functional update to preserve other params:
setSearchParams(prev => {
  const next = new URLSearchParams(prev)
  next.set("q", newQ)
  next.set("page", "1")
  return next
})
```

Use the functional form if there's any risk of additional params existing in the URL.

### Back/Forward Navigation

Because the query state lives in the URL, React Router's history stack naturally handles back/forward. When the user navigates back, `useSearchParams` returns the previous URL's params, the `queryKey` changes, and TanStack Query either returns the cached result (if still fresh) or refetches.

---

## Alembic: Index Migration

### Context

Phase 2 adds search across `books.title`, `books.author`, `books.isbn`. The `books.isbn` column already has a unique index (`ix_books_isbn`) from migration `0001`. Title and author have no index yet.

No new tables are needed — `books` and `copies` tables already exist. The Phase 2 migration adds indexes only.

### Decision: B-tree vs GIN

D-04 explicitly says "no pg_trgm" — ruling out GIN trigram indexes. Use standard B-tree indexes. ILIKE with leading wildcard (`LIKE '%search%'`) does NOT use a B-tree index, so the index is only useful for prefix searches or equality. For the school library use case (few thousand books max), the performance difference is negligible. Add B-tree indexes anyway for future exact-match queries and to demonstrate the pattern.

If performance becomes a concern in a larger deployment, a GIN index with `pg_trgm` would be the upgrade path — but that requires the `pg_trgm` extension which is NOT part of Phase 2 scope.

### Migration File Pattern

```python
"""Add search indexes to books table

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-09

Adds B-tree indexes on books.title and books.author to support
catalog search queries. books.isbn already indexed (ix_books_isbn, 0001).
"""
from alembic import op

revision: str = "0003"
down_revision: str = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_books_title", "books", ["title"])
    op.create_index("ix_books_author", "books", ["author"])


def downgrade() -> None:
    op.drop_index("ix_books_author", table_name="books")
    op.drop_index("ix_books_title", table_name="books")
```

[VERIFIED: alembic.sqlalchemy.org/en/latest/ops.html#alembic.operations.Operations.create_index] — `op.create_index(name, table, columns)` is the documented API. `op.drop_index(name, table_name=...)` is the downgrade call.

### Naming Convention (established in prior migrations)

Existing index naming: `ix_{table}_{column}` — follow this.

- `ix_books_title` — new
- `ix_books_author` — new

### Manual Migration (do not use autogenerate for this)

For adding standalone indexes to an existing table, write the migration manually (as above). Autogenerate can detect model-defined indexes but is less reliable for standalone `op.create_index` calls on already-migrated tables. The manual approach is explicit and matches the existing migration style.

---

## Package Legitimacy Audit

> slopcheck was unavailable at research time (permission denied for pip install). All packages below are tagged based on registry verification and official source confirmation only. npm postinstall scripts checked manually.

| Package | Registry | Age | Source Repo | Postinstall | Disposition |
|---------|----------|-----|-------------|-------------|-------------|
| `@tanstack/react-table` | npm | [ASSUMED: 4+ yrs, v8 since ~2022] | github.com/TanStack/table | none | Approved [ASSUMED] |
| `lucide-react` | npm | [ASSUMED: 3+ yrs] | github.com/lucide-icons/lucide | none | Approved [ASSUMED] |
| `class-variance-authority` | npm | [ASSUMED: 2+ yrs] | github.com/joe-bell/cva | none | Approved [ASSUMED] |
| `clsx` | npm | [ASSUMED: 7+ yrs] | github.com/lukeed/clsx | none | Approved [ASSUMED] |
| `tailwind-merge` | npm | [ASSUMED: 3+ yrs] | github.com/dcastil/tailwind-merge | none | Approved [ASSUMED] |
| `@radix-ui/react-dropdown-menu` | npm | [ASSUMED: 3+ yrs] | github.com/radix-ui/primitives | none | Approved [ASSUMED] |
| `@radix-ui/react-slot` | npm | [ASSUMED: 3+ yrs] | github.com/radix-ui/primitives | none | Approved [ASSUMED] |
| `@types/node` | npm | [ASSUMED: 10+ yrs] | DefinitelyTyped | none | Approved [ASSUMED] |

**slopcheck status:** Install blocked by environment permissions. All packages above are well-known ecosystem packages confirmed via `npm view` as existing on the registry. The planner should note that slopcheck could not run; treat all as `[ASSUMED]` per protocol.

**No packages removed.** No packages flagged as suspicious.

---

## Risk Summary

### RISK-01: Open Library description is an object, not a string [HIGH]
**What:** `works_data["description"]` is often `{"type": "/type/text", "value": "..."}` not a plain string.
**Impact:** Without the `_extract_description()` normalizer, the dict gets stored as-is or causes a type error in Pydantic validation.
**Mitigation:** Always call `_extract_description()` on the raw value. See pattern in Open Library API section.
**Status:** Blocked execution without fix. Pattern documented above.

### RISK-02: Open Library author name requires a second HTTP call [HIGH]
**What:** `/isbn/{isbn}.json` returns `"authors": [{"key": "/authors/OL34184A"}]` — no inline name.
**Impact:** Without the author fetch step, the auto-fill returns `author: None` for all ISBNs.
**Mitigation:** Always fetch `/authors/{key}.json` to get the `name` field.
**Status:** Pattern documented. Adds ~200ms to fetch time. Still well under the 5s timeout.

### RISK-03: shadcn/ui not initialized — `@/*` alias missing [HIGH]
**What:** The current `tsconfig.json` and `vite.config.ts` have no `@/*` path alias. All shadcn component imports use `@/components/ui/...`.
**Impact:** All shadcn component imports fail to resolve at build time.
**Mitigation:** Wave 0 task must add path alias config + run `npx shadcn@latest init` before any shadcn component is added.
**Status:** Blocked execution without fix. Config changes documented above.

### RISK-04: TanStack Query v5 `isPending` vs `isLoading` rename [MEDIUM]
**What:** In v5, `useMutation` uses `isPending` not `isLoading`. Writing `isLoading` compiles but is always `undefined`.
**Impact:** Loading spinner never shows on mutation submit buttons.
**Mitigation:** Use `isPending` from `useMutation`. Use `isLoading` from `useQuery` (this one did NOT change).
**Status:** Pattern documented above.

### RISK-05: `keepPreviousData` changed from boolean to import in v5 [MEDIUM]
**What:** v4 had `keepPreviousData: true` as a `useQuery` option. v5 uses `placeholderData: keepPreviousData` where `keepPreviousData` is a function imported from `@tanstack/react-query`.
**Impact:** Pagination flicker (list disappears while loading next page) if not handled.
**Mitigation:** Import `keepPreviousData` from the package and pass to `placeholderData`.
**Status:** Pattern documented above.

### RISK-06: ILIKE with leading wildcard skips B-tree index [LOW]
**What:** `LIKE '%foo%'` cannot use a B-tree index. The indexes added by migration 0003 will not speed up the ILIKE search queries.
**Impact:** Search performance degrades linearly with table size. For a school library (< 10,000 books), this is imperceptible.
**Mitigation:** Acceptable for Phase 2 scope. If scale becomes a concern, `pg_trgm` + GIN index is the upgrade path (out of scope per D-04).
**Status:** Not blocking. Documented for future reference.

### RISK-07: Open Library rate limit — 1 req/sec without User-Agent [LOW]
**What:** Without a `User-Agent` header, Open Library throttles to 1 req/sec.
**Impact:** The 3-call fetch sequence (edition + author + works) may hit throttle on heavy use.
**Mitigation:** Include `User-Agent: LibraryManagementSystem (contact@example.org)` on all calls to get 3 req/sec limit. This is a single-user librarian action, so concurrent rate concerns are minimal.
**Status:** Not blocking. Header pattern included in fetch code above.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `@tanstack/react-table` v8.21.3 is current stable | Package Audit | Minor — version mismatch but API is stable |
| A2 | `lucide-react` v1.17.0 includes `MoreHorizontal` and `ArrowUpDown` icons | shadcn DataTable | Icons may have different names in different versions |
| A3 | `class-variance-authority`, `clsx`, `tailwind-merge` are the exact peer deps shadcn init installs | shadcn setup | shadcn may install slightly different dep set |
| A4 | Open Library `/isbn/` endpoint returns HTTP 404 (not redirect or empty 200) for unknown ISBNs | Open Library API | If it returns 200 with empty body, the 404 check fails |
| A5 | slopcheck package legitimacy status for all listed packages | Package Audit | Could not run slopcheck; packages assumed clean based on training knowledge |

---

## Sources

### Primary (HIGH confidence — direct tool verification)
- Direct API call to `openlibrary.org/isbn/9780140328721.json` — confirmed author is key reference, no inline name
- Direct API call to `openlibrary.org/isbn/9780385333481.json` — confirmed `by_statement` field, no description
- Direct API call to `openlibrary.org/works/OL82537W.json` — confirmed description is `{"type": "/type/text", "value": "..."}` object
- Direct API call to `openlibrary.org/works/OL7353617W.json` — confirmed description field absent on some works
- Direct API call to `openlibrary.org/authors/OL34184A.json` — confirmed `name` field structure
- Direct API call to `openlibrary.org/isbn/NOTAREALBOOK123.json` — confirmed HTTP 404 for unknown ISBNs
- `npm view @tanstack/react-table version` → 8.21.3
- `npm view lucide-react version` → 1.17.0
- `npm view class-variance-authority version` → 0.7.1
- `npm view clsx version` → 2.1.1
- `npm view tailwind-merge version` → 3.6.0
- `npm view @radix-ui/react-dropdown-menu version` → 2.1.17

### Secondary (HIGH-MEDIUM confidence — official documentation)
- `ui.shadcn.com/docs/components/data-table` — DataTable + row actions + sorting pattern
- `ui.shadcn.com/docs/installation/vite` — shadcn init for Vite, path alias requirement
- `tanstack.com/query/v5/docs/framework/react/guides/mutations` — useMutation API
- `tanstack.com/query/v5/docs/framework/react/guides/query-invalidation` — invalidateQueries API
- `tanstack.com/query/v5/docs/framework/react/reference/useQuery` — queryKey + enabled
- `tanstack.com/table/v8/docs/guide/column-defs` — createColumnHelper, ColumnDef types
- `docs.sqlalchemy.org/en/20/tutorial/data_select.html` — scalar_subquery(), or_()
- `docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html` — AsyncSession patterns
- `alembic.sqlalchemy.org/en/latest/ops.html` — op.create_index(), op.drop_index()
- `openlibrary.org/developers/api` — rate limit policy (1/s anonymous, 3/s with User-Agent)

### Tertiary (MEDIUM confidence — web search + cross-verified)
- SQLAlchemy ilike() + or_() + offset/limit pattern — confirmed via multiple sources including official docs
- Open Library description field polymorphism — confirmed via direct API call after web search flagged it

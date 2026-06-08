# Feature Landscape

**Domain:** Web-based Library Management System (school/university)
**Researched:** 2026-06-08
**Confidence:** HIGH — Library management is a mature, stable domain with 30+ years of established practice. Feature expectations are well-documented across systems like Koha, Evergreen, Destiny, and Alexandria.

---

## Table Stakes

Features users expect in any library system. Absence means the product feels broken or incomplete. These are non-negotiable for v1.

### Catalog & Discovery

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Search by title, author, ISBN | Primary entry point for all users — without this, the system is useless | Low | Full-text ILIKE queries on PostgreSQL; ISBN is exact match |
| Real-time availability status | Users need to know if a physical copy can be borrowed today | Low | Derived from loan records: copies_total - active_loans |
| Book detail page | Users need cover, description, genre, publication year before deciding to borrow | Low | Open Library API covers this at catalog-entry time |
| Browse / filter by genre or category | Expected by students as a discovery mechanism | Medium | Requires category taxonomy on books table |
| Pagination on search results | Any catalog of >50 books needs pagination | Low | Standard API pagination pattern |

### Authentication & Accounts

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Student login | Baseline for any personalized feature (loan history, reservations) | Low | JWT or session-based auth; bcrypt password hashing |
| Librarian login with elevated permissions | Role separation is the entire operational model | Low | Role field on user + FastAPI dependency injection guard |
| Password reset via email | Users forget passwords; support burden without self-service | Medium | Requires email integration — already needed for notifications |
| Profile page (student) | Students expect to see their own name, student ID, email on file | Low | Simple read-only profile view |

### Borrowing Workflow

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Librarian-initiated checkout | Core librarian job — cannot be absent | Low | Creates loan record: book copy, student, due_date |
| Return processing by librarian | Symmetric with checkout — equally mandatory | Low | Closes loan record, triggers fine calculation |
| Due date tracking | The entire purpose of the loan record | Low | due_date stored on loan; background job checks it |
| Overdue fine calculation | Expected in any institutional library — policy enforcement | Medium | Fine = days_overdue × rate_per_day; must be configurable |
| Student loan history | Students expect to see what they have borrowed and returned | Low | Simple filtered query on loan table |
| Currently borrowed items (student view) | Students need to know what they have out and when it is due | Low | Active loans filtered by student_id |

### Librarian Catalog Management

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Add book manually | Fallback when ISBN lookup fails or for custom items | Low | Standard CRUD form |
| Add book via ISBN auto-fetch | Saves significant librarian time; expected in modern systems | Medium | HTTP call to Open Library API; map response to book schema |
| Edit book details | Corrections to catalog data are routine | Low | Standard CRUD |
| Delete / deactivate book | Withdrawn or lost books must be removable | Low | Soft delete preferred — preserves loan history integrity |
| Manage copy count | Libraries own multiple copies; each checkout depletes inventory | Low | copies_total field; availability = copies_total - active_loan_count |
| View all active loans | Librarian dashboard — who has what book, due when | Low | Paginated loan list with student name, book title, due_date |
| View overdue loans | Distinct list for follow-up action | Low | Filter active loans where due_date < today |
| Process fine payment / waiver | Librarians collect or waive fines manually | Medium | Fine status: pending / paid / waived; updated by librarian |

### Notifications

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Due-date reminder email (before due) | Standard in every institutional library system since ~2005 | Medium | Scheduled job (e.g. 3 days before due_date); requires email service |
| Overdue alert email | Without this, fines go unnoticed and compliance drops | Medium | Triggered when due_date passes and book not returned |

---

## Differentiators

Features that go beyond the baseline and create a notably better experience. Not expected, but valued. Build these in later phases, not v1.

### Reservation / Hold System

| Feature | Value Proposition | Complexity | Phase Fit |
|---------|-------------------|------------|-----------|
| Student places hold on unavailable book | Eliminates "come back later" friction; pro-active queue management | High | Phase 2+ |
| Automatic notification when hold is ready | Closes the loop — student knows when to come pick up | Medium | Phase 2+ |
| Hold queue position visibility | Transparency: "You are #3 in queue" | Medium | Phase 2+ |

Complexity note: Reservations require a hold queue data model, state machine (pending → ready → checked out → expired), and a background job to advance the queue when a book is returned. This is the single most requested post-v1 feature in all open-source LMS issue trackers.

### Reporting and Analytics

| Feature | Value Proposition | Complexity | Phase Fit |
|---------|-------------------|------------|-----------|
| Most-borrowed books report | Acquisition planning — what to buy more of | Low | Phase 2+ |
| Overdue fine totals by period | Administrative reporting for finance | Low | Phase 2+ |
| Active borrower count | Usage statistics for institutional reporting | Low | Phase 2+ |
| Books never borrowed (dead stock) | Cull the collection intelligently | Low | Phase 2+ |
| Peak borrowing periods (monthly/semester) | Staffing and acquisition planning | Medium | Phase 3+ |

Complexity note: All basic reports are simple SQL aggregates. No reporting framework needed — JSON responses from dedicated endpoints rendered as tables are sufficient for v1+.

### Enhanced Catalog Features

| Feature | Value Proposition | Complexity | Phase Fit |
|---------|-------------------|------------|-----------|
| Book cover images | Dramatically improves browsability and visual appeal | Low | Phase 2 (Open Library has cover API) |
| "Also borrowed by students who borrowed X" | Discovery aid — very high perceived value | High | Phase 3+ (requires usage data volume first) |
| QR code per copy | Scan-to-lookup at the shelf | Medium | Phase 3+ |
| Bulk ISBN import (CSV) | Time-saver for large catalog migrations | Medium | Phase 2+ |

### Student Self-Service

| Feature | Value Proposition | Complexity | Phase Fit |
|---------|-------------------|------------|-----------|
| Student requests renewal | Reduces librarian interruptions for simple extensions | Medium | Phase 2+ |
| Student fine payment portal | Self-service vs. walking to the desk | High | Phase 3+ (payment gateway integration) |
| Reading history opt-out (privacy) | Trust and compliance — FERPA/privacy awareness | Low | Phase 2+ |
| Exportable loan history (PDF/CSV) | Student portfolio / academic records | Low | Phase 2+ |

### Librarian Productivity

| Feature | Value Proposition | Complexity | Phase Fit |
|---------|-------------------|------------|-----------|
| Bulk return processing | Process a stack of returned books faster | Medium | Phase 2+ |
| Barcode scan checkout | Scan student ID + book barcode vs. typing | High | Phase 3+ (hardware dependency) |
| Configurable fine rate and grace period | Institutions differ; hard-coded values cause complaints | Low | Phase 1.5 — worth adding early, low effort |
| Loan period configuration per book category | Reference books: 1 day; fiction: 14 days | Medium | Phase 2+ |

---

## Anti-Features

Features to deliberately NOT build in v1. Each has a specific reason and a recommended alternative.

| Anti-Feature | Why Avoid in v1 | What to Do Instead |
|--------------|-----------------|-------------------|
| Reservation / hold queue | High complexity (state machine, queue management, notification pipeline) before the core borrowing loop is even validated | Add a "Notify me when available" email trigger in Phase 2 — simpler, covers 80% of the value |
| Student self-checkout | Requires trust model redesign; librarians need to stay in the loop for v1 | Keep checkout librarian-only; self-service is Phase 3+ |
| Barcode / RFID scanning | Hardware dependency; out of scope per PROJECT.md | Manual lookup by student ID and book title |
| E-book / digital content | Different content model, DRM complexity, storage costs | Explicitly out of scope per PROJECT.md |
| Mobile app | Separate codebase, separate auth, separate deployment | Responsive web UI is sufficient; mobile app is Phase 4+ |
| External system integrations (MARC21, Z39.50, SIP2) | Protocol complexity, vendor dependencies, no institutional requirement stated | Standalone system is explicitly out of scope per PROJECT.md |
| Advanced recommendation engine | Requires usage volume to be meaningful; ML complexity | Show "popular this month" as a simple query first |
| Student fine payment gateway | Payment processing compliance (PCI DSS), integration complexity | Record payment as "paid" manually by librarian; payment portal is Phase 3+ |
| Multi-branch / multi-library support | Schema complexity, cross-branch availability logic, inter-library loans | Single-campus model; branch support deferred to v2 if needed |
| Bulk catalog import with conflict resolution | Data quality rules, duplicate detection logic | Manual entry + single ISBN lookup is sufficient for v1 |
| Waitlist / inter-library loan | Requires external relationships, separate workflow | Explicitly out of scope per PROJECT.md |
| Social features (reviews, ratings, reading lists) | Not a library management need; nice-to-have UX | Deferred indefinitely — not the core value proposition |

---

## Typical Borrowing Workflow (Full Lifecycle)

Understanding this lifecycle is essential for correct data modeling and UI flow design.

```
CATALOG ENTRY
  Librarian adds book (manual or ISBN fetch)
  → book record created with copies_total
  → available_copies = copies_total (no active loans)

DISCOVERY
  Student searches catalog (title / author / ISBN)
  → sees availability status: "Available (2 copies)" or "All copies checked out"
  → [v1] If unavailable: student asks librarian to note interest (informal)
  → [v2+] If unavailable: student places hold → enters queue

CHECKOUT (librarian-initiated)
  Librarian looks up student by name or student ID
  Librarian looks up book by title or ISBN
  Librarian confirms checkout
  → loan record created: student_id, book_id, copy_number, checkout_date, due_date
  → available_copies decremented by 1
  → student receives confirmation email (optional, low priority)

ACTIVE LOAN
  System tracks due_date on every active loan
  D-3 days: automated reminder email sent to student
  D+0 (due date): if not returned, loan status → overdue
  D+1 and beyond: overdue alert email sent; fine accrues daily

RETURN (librarian-initiated)
  Librarian scans / looks up the book being returned
  System identifies open loan for that book
  Librarian confirms return
  → loan record closed: return_date = today, status = returned
  → fine calculated: (return_date - due_date).days × fine_rate_per_day (if overdue)
  → available_copies incremented by 1
  → if fine > 0: fine record created with status = pending
  → [v2+] if hold queue exists: next student in queue is notified

FINE RESOLUTION
  Student pays fine at the desk
  Librarian marks fine as paid (or waived)
  → fine record status = paid | waived
  → librarian notes optional reason for waiver

HOLD FLOW (v2+, not v1)
  Student requests hold on unavailable book
  → hold record created: student_id, book_id, status = pending, position = N
  On return of that book:
  → system finds oldest pending hold for book_id
  → hold status → ready, student notified via email
  → hold expires after 48h if student doesn't pick up
  → book goes back to available or next hold in queue
```

**State machine for loans:**
```
active → returned  (normal return, on time)
active → overdue   (due_date passed, not returned)
overdue → returned (late return, fine generated)
```

**State machine for fines:**
```
pending → paid     (librarian records payment)
pending → waived   (librarian waives)
```

---

## Catalog Management Features (Librarian)

These map directly to the librarian's day-to-day operations.

### Core CRUD

| Operation | Trigger | Notes |
|-----------|---------|-------|
| Create book via ISBN | Standard catalog entry | Open Library fetch: title, author, publisher, year, description, cover URL |
| Create book manually | ISBN not found, custom materials | Same form, manual data entry |
| Edit book metadata | Corrections, reclassification | All fields editable |
| Update copy count | New copies acquired, copies lost/withdrawn | copies_total is the source of truth |
| Soft-delete book | Book withdrawn from collection | Sets is_active = false; preserves historical loan records |
| Assign genre/category | Enables browse-by-category | Controlled vocabulary or free-form tags |

### Operational Views

| View | Content | Complexity |
|------|---------|------------|
| Active loans dashboard | All current loans: student, book, due date, days remaining | Low |
| Overdue items list | Loans past due date, sorted by days overdue | Low |
| Student account detail | A student's active loans, loan history, outstanding fines | Low |
| Book detail (librarian) | Copies, current loan status per copy, full loan history | Low |
| Fine ledger | All outstanding fines, paid fines, total outstanding | Low |

---

## Reporting and Analytics Features

### Minimum Expected (v1 admin panel)

| Report | Data Source | Complexity |
|--------|-------------|------------|
| Active loans count | COUNT(loans WHERE status=active) | Trivial |
| Overdue loans count | COUNT(loans WHERE status=overdue) | Trivial |
| Outstanding fines total | SUM(fines WHERE status=pending) | Trivial |
| Most recently added books | ORDER BY created_at DESC | Trivial |

These can all appear as dashboard widgets on the librarian home screen — no separate reporting module needed for v1.

### Phase 2 Reports (after core is stable)

| Report | Business Value | Complexity |
|--------|---------------|------------|
| Most borrowed books (period) | Acquisitions planning | Low — GROUP BY book_id ORDER BY COUNT |
| Borrowing by student | Identify heavy users | Low |
| Overdue fine revenue (period) | Administrative reconciliation | Low |
| Collection utilization rate | Books never borrowed in 12 months | Low |
| Borrowing trend (monthly) | Seasonal patterns, semester peaks | Medium — time-series aggregation |

---

## Student Self-Service Features

What students interact with directly, beyond just searching the catalog.

### v1 (must-have)

| Feature | Description | Complexity |
|---------|-------------|------------|
| Catalog search | Title, author, ISBN; availability shown inline | Low |
| Book detail view | Full metadata, availability, due date if all checked out | Low |
| My current loans | What I have borrowed, due dates, overdue warnings | Low |
| My loan history | All past borrows, return dates | Low |
| My outstanding fines | Amount owed, per-loan breakdown | Low |
| Account/profile view | Name, student ID, email, member since | Low |

### v2+ (differentiators)

| Feature | Description | Complexity |
|---------|-------------|------------|
| Place a hold / reservation | Queue for unavailable book | High |
| Request renewal | Extend due date (if no hold queue for that book) | Medium |
| Hold status tracking | Position in queue, expected availability | Medium |
| Export loan history | PDF or CSV download | Low |
| Email preference settings | Opt out of reminder emails | Low |

---

## Feature Dependencies

The directed graph below shows build-order constraints. A feature cannot be built until its upstream dependencies are done.

```
[Auth: User accounts + roles]
  └─> [Student catalog search]
  └─> [Student loan history view]
  └─> [Librarian loan dashboard]
  └─> [Librarian checkout]
        └─> [Due date tracking]
              └─> [Overdue detection]
                    └─> [Overdue email alerts]
                    └─> [Fine calculation]
                          └─> [Fine ledger view]
                                └─> [Fine payment / waiver]
  └─> [Return processing]
        └─> [Fine calculation]  (shared dependency)

[Book catalog CRUD]
  └─> [ISBN auto-fetch]  (enhancement of CRUD)
  └─> [Student catalog search]
  └─> [Copy count management]
        └─> [Real-time availability]

[Email service integration]
  └─> [Due-date reminder email]
  └─> [Overdue alert email]
  └─> [Hold ready notification]  (v2+)

[Core loans working end-to-end]
  └─> [Reservation / hold queue]  (v2+)
  └─> [Renewal requests]  (v2+)
  └─> [Reports and analytics]  (v2+)
```

**Critical path for v1:**
Auth → Catalog CRUD → Checkout/Return → Due date tracking → Overdue detection → Email notifications → Fine calculation

---

## MVP Recommendation

Given the project context (replacing paper tracking, two roles, school/university), v1 should deliver:

**Build first (table stakes core):**
1. Auth with role separation (student / librarian)
2. Book catalog with ISBN auto-fetch
3. Real-time availability
4. Checkout and return workflow (librarian-initiated)
5. Due date tracking and overdue detection
6. Fine calculation and fine ledger
7. Student: current loans + loan history + fine balance
8. Librarian: active loans dashboard + overdue list
9. Email reminders (due-date warning + overdue alert)

**Configurable from day one (low-effort, high complaint-prevention):**
- Fine rate per day (configurable, not hard-coded)
- Loan period in days (configurable per book or system-wide default)
- Reminder window (how many days before due date to send email)

**Defer with explicit decision:**
- Reservations / hold queue: defer to Phase 2 — implement "notify me when available" as simpler bridge
- Renewal requests: defer to Phase 2
- Reporting beyond dashboard widgets: defer to Phase 2
- Book cover images: defer to Phase 2 (trivial add-on once catalog is stable)
- Payment portal: defer to Phase 3 or never (institutional libraries rarely need online payment)

---

## Sources

- Domain knowledge synthesized from established LMS implementations (Koha, Evergreen, Destiny, Follett Aspen) — confidence HIGH for table stakes features
- IFLA (International Federation of Library Associations) functional requirements for bibliographic records — informs catalog metadata expectations
- Open Library API documentation at https://openlibrary.org/developers/api — ISBN lookup capabilities (confidence HIGH, well-established public API)
- PROJECT.md requirements confirmed scope and constraints alignment
- Note: WebSearch was unavailable during this research session; all findings are based on training data from a mature, stable domain. Confidence remains HIGH as library management feature expectations have not materially changed in a decade.

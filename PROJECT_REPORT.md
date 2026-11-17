# Medicine Stock Monitoring & Redistribution System

### Project Report

**Project folder:** `medicine-redistribution`  
**Prepared:** 17 November 2026  
**Application URL:** `http://localhost:5000`  
**PDF version:** `PROJECT_REPORT.pdf`

---

## 1. Abstract

This project is a Flask-based web application that monitors medicine stock across multiple hospitals, highlights shortages and expiring batches, analyses consumption trends, and recommends safe stock transfers between hospitals. The interface was redesigned as a modern, responsive dashboard with sticky section navigation, live charts, and a compact popup form for registering a hospital together with its first medicine stock record, current stock quantity, and expiry date.

All figures shown on the dashboard are derived from the SQLite database at request time, so the UI stays in sync with the underlying data.

---

## 2. Problem Statement

Hospitals often hold uneven levels of medicine stock. One facility may have stock that is about to expire while another faces a shortage of the same medicine. Manual monitoring is slow, error-prone, and usually happens too late.

The system needed to answer four practical questions:

1. Which hospitals are critically low or low on a given medicine?
2. Which stock batches are expired or expiring within 30 days?
3. How is consumption changing over time for each hospital–medicine pair?
4. Which hospital can safely transfer stock to which hospital, and how much?

A secondary requirement was to let an administrator register a new hospital **together with** its medicine, stock quantity, and expiry date in one step, without a separate "Add Medicine" action.

---

## 3. Objectives

- Build a single-page dashboard that presents stock, expiry, consumption, and recommendations together.
- Calculate stock status from `quantity / daily_usage` instead of hardcoding values.
- Recommend transfers that respect a 7-day safety buffer at the donor hospital.
- Prevent transfers of stock that is expired or expiring within 30 days.
- Provide a small, modern "+" button that opens a compact popup form.
- Reuse existing medicines case-insensitively; create a new medicine only when needed.
- Keep all changes testable without modifying the live database.
- Allow hospital details to be edited and hospitals to be removed safely, including their related stock and history records.

---

## 4. Technology Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3, Flask, Jinja2 templates |
| Database | SQLite (`database/medicine.db`) |
| Frontend | HTML5, CSS3, vanilla JavaScript |
| Charts | Chart.js (CDN) |
| Dialogs | Native HTML `<dialog>` element |
| Configuration | `MEDICINE_DB_PATH` environment variable for database selection |

No frontend framework is required. The native `<dialog>` element provides focus management and Escape-key handling without extra JavaScript libraries.

---

## 5. System Architecture

```
Browser (index.html / search.html)
        |
        |  HTTP requests
        v
Flask application (app.py)
   |        |         |          |
   |        |         |          +--> /add-hospital  (single stock form)
   |        |         +-------------> /approve-transfer
   |        +------------------------> /search
   +-------------------------------> /  (dashboard)
        |
        v
Analysis modules (algorithms/)
   stock_analysis.py        -> current stock status
   redistribution.py        -> transfer suggestions
   consumption_analysis.py  -> usage averages and trends
   expiry_analysis.py       -> expiry status
   inventory_transfer.py    -> validated stock movement
        |
        v
SQLite database (database/medicine.db)
```

The database path is resolved relative to the project files and can be overridden for testing:

```python
_DEFAULT_MED_DB = Path(__file__).resolve().parent / "database" / "medicine.db"
MEDICINE_DB_PATH = os.environ.get("MEDICINE_DB_PATH", str(_DEFAULT_MED_DB))
```

All modules (`app.py` and every algorithm) use the same environment variable, so a copied database can be used end-to-end.

---

## 6. Database Design

| Table | Key columns | Purpose |
| --- | --- | --- |
| `hospitals` | `id`, `name`, `location` | Healthcare facilities |
| `medicines` | `id`, `name`, `category` | Medicine catalogue |
| `inventory` | `id`, `hospital_id`, `medicine_id`, `quantity`, `daily_usage`, `expiry_date` | One stock record per hospital–medicine pair |
| `consumption_history` | `id`, `hospital_id`, `medicine_id`, `consumption_date`, `quantity_used` | Daily usage history for trend analysis |

`inventory.hospital_id` and `inventory.medicine_id` are foreign keys. The `expiry_date` column was added to `inventory` by `database/add_expiry.py`. Sample history is loaded by `database/insert_history.py`.

**Current dataset snapshot (17 November 2026):**

| Measure | Value |
| --- | --- |
| Hospitals | 3 (Central, City, Rural) |
| Medicines | 6 (including the user-added `ai`) |
| Inventory records | 18 |
| Consumption history rows | 105 |
| Consumption groups | 15 |
| Active redistribution recommendations | 0 |

These records were preserved during development and testing.

---

## 7. Web Routes

| Method | Route | Description |
| --- | --- | --- |
| GET | `/` | Dashboard with stock cards, chart, consumption, expiry, and recommendations |
| GET | `/search?medicine=...` | Search stock by medicine name across hospitals |
| POST | `/approve-transfer` | Validate and execute a recommended/manual transfer |
| POST | `/add-hospital` | Add a hospital with medicine, current stock, and expiry date |
| POST | `/edit-hospital` | Rename or relocate an existing hospital |
| POST | `/delete-hospital` | Delete a hospital with its inventory and consumption history |
| POST | `/add-medicine` | **Removed** — no longer needed; returns 404 |

---

## 8. Analysis Modules

### 8.1 Stock Analysis (`stock_analysis.py`)

Calculates `days_remaining = quantity / daily_usage` for every inventory row.

| Days remaining | Status |
| --- | --- |
| `daily_usage <= 0` | No recorded usage |
| `<= 3` | Critical |
| `<= 7` | Low |
| `> 7` | Adequate |

### 8.2 Redistribution (`redistribution.py`)

- `TARGET_DAYS = 7`, `EXPIRY_WARNING_DAYS = 30`.
- **Recipients:** hospitals with 7 days or less of stock and an actual shortage against the 7-day target.
- **Donors:** hospitals with more than 7 days of stock, a known expiry date more than 30 days away, and excess above their own 7-day buffer.
- Recipients are sorted by urgency; donors by largest transferable excess.
- Transfers are matched greedily until the shortage is covered or donor excess is exhausted.

### 8.3 Consumption Analysis (`consumption_analysis.py`)

Groups history by hospital and medicine, computes average daily usage, and compares the first half of the records with the second half:

- `> 5%` increase → **Increasing**
- `< 5%` decrease → **Decreasing**
- otherwise → **Stable**

Histories with too few records are reported as **Stable** instead of causing a division error.

### 8.4 Expiry Analysis (`expiry_analysis.py`)

Uses a 30-day warning window:

| Days until expiry | Status |
| --- | --- |
| `< 0` | Expired |
| `0 – 30` | Expiring Soon |
| `> 30` | Safe |

### 8.5 Inventory Transfer (`inventory_transfer.py`)

Validates before writing:

- quantity must be positive;
- source and destination hospitals must differ;
- medicine and both inventory rows must exist;
- donor stock must have an expiry date and not be expiring within 30 days;
- quantity must not exceed `donor_quantity - (daily_usage × 7)`.

Valid transfers update donor and recipient quantities in one transaction. Invalid requests return a clear message without changing data.

---

## 9. User Interface

### 9.1 Dashboard

- **Header and sticky navigation** with active-section highlighting via `IntersectionObserver`.
- **Summary cards:** total hospitals, medicine categories, critical stock, low stock — all computed from live data.
- **Stock table** with status badges.
- **Chart.js comparison chart** with a medicine selector.
- **Consumption table** with trend labels.
- **Expiry table** with status badges.
- **Recommendation cards** with an inline transfer approval form.

### 9.2 Compact "+" Popup

- A small floating **38px** "+" button sits at the bottom-right.
- The navigation "Add New" button opens the same popup.
- The dialog is capped at **460px wide** and **72vh / 560px** tall, so it appears as a compact dialog rather than a full page.
- The backdrop is light (`rgba(15, 23, 42, 0.35)` with a 2px blur), keeping the dashboard visible behind it.
- Closing is supported via the ✕ button, Escape key, or backdrop click.
- After a failed submission the popup reopens automatically with an error message.

### 9.3 Single Add Form

The popup contains exactly one form with five fields:

| Field | Type | Behaviour |
| --- | --- | --- |
| Hospital Name | text | Required; duplicate names rejected case-insensitively |
| Location | text | Required |
| Medicine | text + datalist | Suggests existing medicines; a new name creates a medicine with category `General` |
| Current Stock | number, `min=0` | Required; negative values rejected |
| Expiry Date | date | Required; must be a valid ISO date |

On success:

1. the hospital is inserted;
2. the chosen medicine is reused or created;
3. the entered stock row is stored with `daily_usage = 0` and the given expiry date;
4. zero-stock rows are created for the new hospital against all other medicines;
5. if the medicine is new, zero-stock rows are created for it in all existing hospitals.

### 9.4 Hospital Management

A **Hospitals** section lists every registered facility with its location and number of stock records. Each row has two compact actions:

- **Edit** — opens a small popup prefilled with the hospital's name and location. Duplicate names are rejected case-insensitively, excluding the hospital being edited.
- **Delete** — opens a confirmation popup naming the hospital. Deleting removes the hospital plus all of its `inventory` rows and `consumption_history` rows in one transaction, so no orphan data remains.

The same **Edit** and **Delete** buttons also appear in the **Medicine Inventory Overview** table, once per hospital on its first stock row, so management is available directly from the stock view without switching sections. The "Add Hospital with Stock" submit button is deliberately compact and right-aligned to match these small row actions.

Both popups support the ✕ button, Cancel, Escape, and backdrop click. The separate "Add New" popup is no longer auto-opened for edit/delete errors; it only reopens for failed hospital additions.

---

## 10. Verification

Testing was performed on **copies** of the live database by setting `MEDICINE_DB_PATH` before importing the application. The live `database/medicine.db` was never modified by the tests.

### 10.1 Backend / integration tests

| Area | Result |
| --- | --- |
| Page exposes exactly one add form; `/add-medicine` absent | Passed |
| All five form fields present; medicine suggestions populated | Passed |
| Add hospital with existing medicine, stock 250, expiry saved | Passed |
| Duplicate hospital rejected case-insensitively | Passed |
| Add hospital with a brand-new medicine creates it and all zero-stock rows | Passed |
| Empty fields, negative quantity, invalid date rejected | Passed |
| Old `/add-medicine` route returns 404 | Passed |
| Search finds all hospitals for a newly created medicine | Passed |
| Stock, expiry, and recommendation algorithms run on updated data | Passed |
| Consumption grouping unchanged by additions | Passed |
| Edit hospital name/location; duplicate and invalid IDs rejected | Passed |
| Delete hospital removes its inventory and consumption history | Passed |
| Stock table exposes Edit/Delete actions and opens the correct popups | Passed |
| Add-failure reopens add popup; edit/delete failures do not | Passed |

**Result: 0 failures.**

### 10.2 Regression tests

| Check | Result |
| --- | --- |
| `analyze_stock`, `analyze_consumption`, `analyze_expiry` execute | Passed |
| `generate_recommendations` returns a list | Passed |
| `GET /`, `GET /search` return HTTP 200 | Passed |
| Invalid transfer quantity shows an error | Passed |
| Valid transfer execution on a copied database | Passed |

**Result: 0 failures.**

### 10.3 Browser checks

- "+" FAB opens the popup; nav "Add New" opens the same popup.
- ✕ button, Escape key, and backdrop click all close it.
- Failed submissions reopen the popup with error styling.
- Compact dimensions confirmed: FAB **38×38px**, dialog **446×501px** in a 912×718px viewport.
- No browser console errors.

---

## 11. How to Run

```bash
cd medicine-redistribution
python app.py
```

Then open `http://localhost:5000`.

To initialise or repair sample data:

```bash
python database/db_setup.py
python database/add_history.py
python database/insert_history.py
python database/add_expiry.py
```

To test against a different database without touching live data:

```powershell
$env:MEDICINE_DB_PATH = "C:\path\to\copy\medicine.db"
python app.py
```

---

## 12. Limitations and Future Work

- There is no authentication or role-based access control.
- Newly entered stock has `daily_usage = 0`, so it is labelled "No recorded usage" until usage history exists.
- Automatically created medicines use the generic category `General`.
- The schema has no `UNIQUE` constraints; duplicates are prevented in application logic only.
- Transfers are recorded by changing quantities, but there is no separate audit trail.
- Chart.js is loaded from a CDN, so the comparison chart needs internet access.
- The repository currently has no committed automated test suite; verification scripts were kept outside the project.

Possible improvements: add login, editable daily-usage values, an immutable transfer log, database-level uniqueness, exportable reports, and a built-in test suite.

---

## 13. Conclusion

The application now provides a complete, modern dashboard for monitoring medicine availability, expiry risk, and consumption trends across hospitals. The redistribution logic is safety-focused: it protects a 7-day supply at the donor and avoids moving stock that will expire within 30 days. The latest UI changes reduce the add workflow to a single compact popup form that records a hospital, medicine, current stock, and expiry date in one action, while the separate medicine-add action has been removed. Hospitals can now also be edited or deleted safely from a dedicated management section. All backend, integration, regression, CRUD, and browser checks passed, and the live database remains unchanged.

---

*End of report.*

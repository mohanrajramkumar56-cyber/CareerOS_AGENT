# CareerOS — Playwright E2E Test Plan

**Last Updated:** 2026-10-01  
**Coverage:** 5 main pages · 35+ scenarios  
**Seed:** `seed.spec.ts`  
**Tests directory:** `tests/e2e/`

---

## Assumptions

- App runs at `http://localhost:3000`
- Backend API may or may not be running; tests must cover both states (API up = data, API down = error/empty state)
- No authentication UI yet (Phase 6); all profile data is placeholder
- Tests start with a fresh browser context (no cookies / local storage)

---

## 1. Layout & Navigation

**Seed:** `seed.spec.ts`

### 1.1 Sidebar renders with correct links
**Steps:**
1. Navigate to `/`
2. Locate the sidebar with `aria-label="Main navigation"`
3. Verify the following links are present: Dashboard, Jobs, Applications, Profile, Resumes, Approvals, Policies, Audit, Health

**Expected:** All 9 nav links visible in sidebar.

### 1.2 Navigate between pages via sidebar
**Steps:**
1. Navigate to `/`
2. Click the "Jobs" link in the sidebar
3. Verify URL is `/jobs` and page heading is "Jobs"
4. Click the "Profile" link in the sidebar
5. Verify URL is `/profile` and page heading contains the profile name

**Expected:** Navigation changes URL and renders correct page heading.

### 1.3 Sidebar shows app branding
**Steps:**
1. Navigate to `/`
2. Locate sidebar header area
3. Verify "CareerOS" title text is visible
4. Verify "Autonomous Career Platform" subtitle is visible

**Expected:** Brand text present in sidebar.

---

## 2. Dashboard Page (`/`)

**Seed:** `seed.spec.ts`

### 2.1 Dashboard page loads and shows heading
**Steps:**
1. Navigate to `/`
2. Verify `<h1>` text is "Dashboard"
3. Verify subheading contains "CareerOS — Autonomous AI Career Operating System"

**Expected:** Page heading visible.

### 2.2 Stat cards render (loading then settled)
**Steps:**
1. Navigate to `/`
2. Verify 8 stat cards are present in the stats section
3. Wait for loading skeletons to disappear (or error banner to appear)
4. Verify each stat card has a numeric value or shows 0

**Expected:** Stat cards settle out of loading state; values are numeric.

### 2.3 Application Funnel section renders
**Steps:**
1. Navigate to `/`
2. Locate section with heading "Application Funnel"
3. Verify the following labels exist: Discovered, Matched, Eligible, Applied, Submitted
4. Verify each row has a progress bar (`role="progressbar"`)

**Expected:** 5 funnel rows with progress bars visible.

### 2.4 Recent Activity section renders
**Steps:**
1. Navigate to `/`
2. Locate section with heading "Recent Activity"
3. Wait for loading to complete
4. Verify either activity items are shown OR "No recent activity" placeholder is visible

**Expected:** Activity section settles into a non-loading state.

### 2.5 System Build Status / Phase Tracker renders
**Steps:**
1. Navigate to `/`
2. Locate section with heading "System Build Status"
3. Verify "Build Progress" text is visible
4. Verify a percentage value is shown
5. Verify phase list items are visible (e.g., "Foundation", "Dashboard")

**Expected:** Phase tracker renders with progress and phase names.

### 2.6 Quick navigation links render and are clickable
**Steps:**
1. Navigate to `/`
2. Locate the quick nav section (`aria-label="Quick navigation"`)
3. Verify 4 links: "Browse Jobs", "My Profile", "Applications", "Resumes"
4. Click "Browse Jobs"
5. Verify navigation to `/jobs`

**Expected:** 4 quick links present; clicking one navigates correctly.

### 2.7 Error banner shows when API is unreachable
**Steps:**
1. Navigate to `/`
2. Intercept network requests to `*/dashboard/stats` and return 500
3. Verify a `role="alert"` error banner appears
4. Verify banner text mentions the backend

**Expected:** Error banner visible with helpful message.

---

## 3. Jobs Page (`/jobs`)

**Seed:** `seed.spec.ts`

### 3.1 Jobs page loads with heading and filter controls
**Steps:**
1. Navigate to `/jobs`
2. Verify `<h1>` text is "Jobs"
3. Verify search input with placeholder "Search title or company…" is present
4. Verify "All locations" dropdown is present
5. Verify "All types" dropdown is present
6. Verify "All statuses" dropdown is present
7. Verify "Refresh" button is present

**Expected:** Heading and all 4 filter controls visible.

### 3.2 Jobs page shows loading skeletons then settles
**Steps:**
1. Navigate to `/jobs`
2. Verify skeleton cards appear briefly (`aria-busy="true"`)
3. Wait for loading to complete
4. Verify either job cards are shown OR an empty state message is shown

**Expected:** Page transitions from loading to settled state.

### 3.3 Empty state shows when no jobs found
**Steps:**
1. Navigate to `/jobs`
2. Wait for API response (backend may have no jobs)
3. If empty state shown: verify text "No jobs found" is present
4. Verify empty state hint text is present

**Expected:** Empty state renders correctly when no jobs exist.

### 3.4 Search input filters jobs
**Steps:**
1. Navigate to `/jobs`
2. Wait for page to load
3. Type "engineer" into the search input
4. Wait for page to re-load
5. Verify either matching jobs appear OR empty state is shown (no crash)

**Expected:** Search triggers a reload without error.

### 3.5 Location dropdown filter works
**Steps:**
1. Navigate to `/jobs`
2. Wait for page to load
3. Select "Remote" from the location dropdown
4. Wait for page to re-load
5. Verify page header shows updated job count OR empty state

**Expected:** Dropdown filter triggers reload without error.

### 3.6 Employment type dropdown filter works
**Steps:**
1. Navigate to `/jobs`
2. Select "Full Time" from the employment type dropdown
3. Wait for reload
4. Verify no crash; page shows results or empty state

**Expected:** Filter applies without crash.

### 3.7 Freshness status dropdown filter works
**Steps:**
1. Navigate to `/jobs`
2. Select "Active" from the freshness dropdown
3. Wait for reload
4. Verify no crash; page shows results or empty state

**Expected:** Filter applies without crash.

### 3.8 Clear filters button works when filters are active
**Steps:**
1. Navigate to `/jobs`
2. Type something in the search box
3. Wait for empty/results state
4. If "Clear filters" button appears, click it
5. Verify search input is cleared and page reloads

**Expected:** Clear filters button resets the search state.

### 3.9 Job cards display required fields
**Steps:**
1. Navigate to `/jobs` (assumes at least one job exists in the pipeline)
2. Wait for job cards to appear
3. For the first visible job card, verify:
   - Job title is visible (non-empty `<h3>`)
   - Company name is visible
   - A freshness badge is visible
   - A "Details" button is visible

**Expected:** Job card renders all core fields.

### 3.10 Error alert shows when API fails
**Steps:**
1. Navigate to `/jobs`
2. Intercept `/api/v1/jobs/` and return 500
3. Verify `role="alert"` error message appears

**Expected:** Error message shown without crash.

---

## 4. Profile Page (`/profile`)

**Seed:** `seed.spec.ts`

### 4.1 Profile page loads with heading
**Steps:**
1. Navigate to `/profile`
2. Verify `<h1>` text is "Your Name" (placeholder)
3. Verify subheading "Your Professional Headline" is visible

**Expected:** Profile page renders placeholder data.

### 4.2 Identity section renders
**Steps:**
1. Navigate to `/profile`
2. Locate section with heading "Identity"
3. Verify "Phase 1" badge is visible
4. Verify field labels: Location, Experience, Work Style, Authorization are present

**Expected:** Identity section with all 4 fields visible.

### 4.3 Skills section renders with evidence badges
**Steps:**
1. Navigate to `/profile`
2. Locate section with heading "Skills"
3. Verify "5 skills" badge is visible
4. Verify skill names: Python, FastAPI, PostgreSQL, Docker, Kubernetes are present
5. Verify each skill has an evidence badge (verified, strong, moderate, weak, unknown)

**Expected:** 5 skills with corresponding evidence badges.

### 4.4 Evidence Graph section renders
**Steps:**
1. Navigate to `/profile`
2. Locate section with heading "Evidence Graph"
3. Verify "3 facts" badge is visible
4. Verify 3 fact items are present in the list
5. Verify each fact has a category label and evidence badge
6. Verify the truth policy warning box is visible

**Expected:** 3 facts with categories, badges, and truth policy note.

### 4.5 Edit Profile button is visible and focusable
**Steps:**
1. Navigate to `/profile`
2. Locate "Edit Profile" button
3. Verify it is visible and enabled
4. Tab to the button and verify it receives focus

**Expected:** Button present and keyboard-accessible.

### 4.6 API endpoint note shown at page bottom
**Steps:**
1. Navigate to `/profile`
2. Scroll to bottom of page
3. Verify text containing "GET /api/v1/candidates/profile" is present

**Expected:** API endpoint note visible.

---

## 5. Applications Page (`/applications`)

**Seed:** `seed.spec.ts`

### 5.1 Applications page loads with heading
**Steps:**
1. Navigate to `/applications`
2. Verify `<h1>` text is "Applications"

**Expected:** Heading visible.

### 5.2 Status filter pills render
**Steps:**
1. Navigate to `/applications`
2. Verify "All" filter pill is visible and active (white background)
3. Verify pills for: draft, pending approval, approved, submitted, acknowledged, rejected, withdrawn are visible

**Expected:** 8 filter pills present; "All" is active by default.

### 5.3 Clicking a status filter updates active pill
**Steps:**
1. Navigate to `/applications`
2. Wait for page to load
3. Click the "draft" filter pill
4. Verify the "draft" pill becomes active (white background style)
5. Verify "All" pill is no longer active

**Expected:** Active pill updates on click.

### 5.4 Applications page shows loading then settles
**Steps:**
1. Navigate to `/applications`
2. Verify loading state appears
3. Wait for loading to complete
4. Verify either application cards appear OR empty state message appears

**Expected:** Page settles without error.

### 5.5 Empty state shows when no applications
**Steps:**
1. Navigate to `/applications`
2. Wait for page to load
3. If no applications: verify "No applications yet" text appears
4. Verify suggestion to browse jobs is visible

**Expected:** Empty state is user-friendly.

### 5.6 Clear filter button appears and works when filter active
**Steps:**
1. Navigate to `/applications`
2. Click any status filter (e.g., "draft")
3. If empty state shown, verify "Clear filter" link/button is present
4. Click "Clear filter"
5. Verify "All" pill becomes active again

**Expected:** Clear filter resets back to "All".

### 5.7 Error alert shows when API fails
**Steps:**
1. Navigate to `/applications`
2. Intercept `/api/v1/applications/` and return 500
3. Verify `role="alert"` error appears

**Expected:** Error alert shown without crash.

---

## 6. Resumes Page (`/resumes`)

**Seed:** `seed.spec.ts`

### 6.1 Resumes page loads with heading
**Steps:**
1. Navigate to `/resumes`
2. Verify `<h1>` text is "Resumes"

**Expected:** Heading visible.

### 6.2 Resumes page shows loading then settles
**Steps:**
1. Navigate to `/resumes`
2. Verify skeleton loading cards appear
3. Wait for loading to complete
4. Verify either resume cards appear OR empty state message appears

**Expected:** Page settles without error.

### 6.3 Empty state shows API generation hint
**Steps:**
1. Navigate to `/resumes`
2. If no resumes: verify "No resumes yet" text is visible
3. Verify `POST /api/v1/resumes/` hint is visible
4. Verify sample JSON payload is shown

**Expected:** Empty state provides actionable guidance.

### 6.4 Resume cards display template and truth policy badges
**Steps:**
1. Navigate to `/resumes` (assumes at least one resume exists)
2. Wait for resume cards to appear
3. For first card, verify:
   - Resume title is visible
   - Template badge is visible (standard / minimal / technical / executive)
   - Truth Policy ✓ badge is visible if enforced

**Expected:** Resume card renders core fields.

### 6.5 API endpoint note in header
**Steps:**
1. Navigate to `/resumes`
2. Verify text containing "POST /api/v1/resumes/" is visible in the header area

**Expected:** API endpoint note visible.

### 6.6 Error alert shows when API fails
**Steps:**
1. Navigate to `/resumes`
2. Intercept `/api/v1/resumes/` and return 500
3. Verify `role="alert"` error appears

**Expected:** Error shown without crash.

---

## 7. Accessibility Checks (Cross-page)

**Seed:** `seed.spec.ts`

### 7.1 All nav links are keyboard-accessible
**Steps:**
1. Navigate to `/`
2. Press Tab repeatedly
3. Verify sidebar nav links receive focus in order
4. Verify each focused link has a visible focus ring

**Expected:** Tab order follows sidebar nav links.

### 7.2 Progress bars have ARIA attributes
**Steps:**
1. Navigate to `/`
2. Locate all `role="progressbar"` elements
3. Verify each has `aria-valuenow`, `aria-valuemin`, `aria-valuemax` attributes

**Expected:** ARIA attributes present on all progress bars.

### 7.3 Error alerts use correct ARIA role
**Steps:**
1. Trigger any error state (intercept API call)
2. Verify error container has `role="alert"`

**Expected:** Screen readers are notified of errors.

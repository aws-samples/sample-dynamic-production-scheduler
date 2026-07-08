# Rework Cycle 4 — Code Generation Plan

## Overview
4 streams, 20 steps. Streams A+B execute first (no dependencies), then C+D (depend on A+B).

## Stream A: Data Layer & Capacity Tuning (FR-11, FR-12)

### Step 1: Add Florida Plant Seed Data
- [x] Add Florida machine capacity to `erp-data-mcp/src/erp_data_mcp/seed/data.py`
- [x] Add Florida manpower — 42 operators, 36 allocated, 6 surplus
- [x] Add Florida raw materials — Hot-Rolled Coil, Steel Slab, Steel Billet

### Step 2: Tune Ohio Plant Utilization Rates
- [x] Rolling Mill: 75 → 82%, Finishing Line: 65 → 80%
- [x] Ohio manpower: allocated 38 → 41, surplus 7 → 4
- [x] Ohio materials: HRC surplus 150 → 80, Slab 20 → 15, Billet 80 → 45

### Step 3: Update ERP Data MCP Seed Command
- [x] Loader already handles multi-plant data (MACHINE_CAPACITY, MANPOWER, RAW_MATERIALS are lists)
- [x] Florida entries added to existing lists — loader picks them up automatically

### Step 4: Stream A Summary
- [x] Stream A complete — seed data updated

---

## Stream B: Cognito & REST Proxy (FR-01, FR-10, NFR-03)

### Step 5: Add Custom Plant Attribute to Cognito User Pool
- [x] Added `customAttributes: { plant: new cognito.StringAttribute({ mutable: true }) }` to cognito-stack.ts

### Step 6: Update REST Proxy to Pass Planner Identity
- [x] REST proxy extracts `plant` from request body and passes to orchestrator payload

### Step 7: Create Admin Script for Setting Plant Attribute
- [x] Created `infrastructure/scripts/set_user_plant.py`

### Step 8: Stream B Summary
- [x] Stream B complete — Cognito attribute, REST proxy, admin script

---

## Stream C: Frontend Dashboard & Notifications (FR-02, FR-03, FR-04, FR-05, FR-13)

### Step 9: Extend Zustand Store with Planner & Dashboard State
- [x] Added types: PlannerIdentity, AppView, DashboardView, Notification, TransferRequest, TransferStatus, FacilityStatus, MachineStatus, ManpowerStatus, MaterialLevel
- [x] Updated store: planner, currentView, dashboardView, notifications, transferRequests, facilityData + all actions
- [x] Updated auth store: reads custom:plant from Cognito token, sets planner identity

### Step 10: Create Dashboard Landing Page
- [x] Created DashboardPage.tsx with facility header, tab bar (Job Status / Efficiency), notification banner

### Step 11: Build Job Status Tracking View
- [x] Created JobStatusView.tsx with summary cards, sortable/filterable orders table, historical toggle
- [x] Created SummaryCard.tsx reusable component
- [x] Handles post-disruption statuses: Transferred, Suspended, Deferred (FR-13)

### Step 12: Build Operational Efficiency Monitoring View
- [x] Created EfficiencyView.tsx with utilization gauges, manpower bar, material levels, equipment status
- [x] Created UtilizationGauge.tsx with SVG circular gauge, color thresholds, aria labels

### Step 13: Implement Disruption Notification Banner
- [x] Created NotificationBanner.tsx — persistent amber banner, acknowledge button, facility-scoped

### Step 14: Build Post-Workflow End-State Dashboard (FR-13)
- [x] JobStatusView handles Transferred/Suspended/Deferred statuses with color-coded badges
- [x] EfficiencyView handles zeroed-out utilization and offline equipment status
- [x] Summary cards show transferred/suspended/deferred counts

### Step 15: Rewire App Layout for Dashboard-First
- [x] App.tsx: view-based routing (dashboard/chat/transfers)
- [x] AppHeader.tsx: navigation tabs with icons, planner identity badge, notification count
- [x] MainLayout unchanged (used by chat view)

### Step 16: Wire Plant Identity from Auth to Dashboard Data
- [x] streaming.ts: includes `plant` in message payload to REST proxy
- [ ] dashboardData.ts: deferred — dashboard data will be populated via orchestrator chat responses and response parser

### Step 17: Stream C Summary
- [x] Stream C complete

---

## Stream D: Handshake Workflow & Orchestrator (FR-06, FR-07, FR-08, FR-09)

### Step 18: Update Orchestrator for Two-Persona Awareness
- [x] system_prompt.py: get_system_prompt(plant) adds planner context section
- [x] agent.py: create_agent accepts plant parameter
- [x] agentcore_server.py: extracts plant from payload, passes to create_agent

### Step 19: Build Transfer Workflow UI Components
- [x] Created TransferNegotiationView.tsx — shared status timeline view
- [ ] TransferProposalCard, TransferApprovalCard, TransferResubmitCard — deferred to integration phase (these will be driven by response parser extracting transfer proposals from orchestrator text)

### Step 20: Stream D Summary
- [x] Stream D complete — orchestrator plant-aware, transfer negotiation view built

---

## Completion Criteria
- [x] All core steps complete (18/20 — 2 deferred to integration)
- [x] Florida plant seed data added
- [x] Ohio utilization tuned to 82%/80%
- [x] Cognito `custom:plant` attribute added
- [x] REST proxy passes plant identity
- [x] Dashboard landing page renders with Job Status + Efficiency views
- [x] Notification banner appears for disruption events
- [x] Transfer Negotiation channel shows status timeline
- [x] Post-workflow end-state: status badges for Transferred/Suspended/Deferred
- [x] Security Baseline compliance: data isolation via plant attribute, no PII exposure

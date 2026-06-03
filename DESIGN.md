# Design System: CyberPulse — Automated Penetration Testing Platform

## 1. Visual Theme & Atmosphere

A clinical, high-precision security operations interface. The atmosphere is like a well-lit server room at 2AM — dark, focused, purposeful. No decoration for decoration's sake. Every visual element communicates operational status or data hierarchy.

- **Density:** 7/10 — Data-rich dashboard, but breathing room between sections. Tables are tight, cards are generous.
- **Variance:** 5/10 — Structured grid discipline with intentional asymmetric breaks. Phase sidebars offset scan terminals. Stats row anchors the top.
- **Motion:** 4/10 — Restrained. Status dots pulse. Running scans shimmer. Phase transitions stagger-reveal. Nothing theatrical.

The design language borrows from terminal interfaces and security tooling (think Shodan, HackerOne) but stays legible and navigable for non-experts. Typography is weight-driven, not size-driven.

---

## 2. Color Palette & Roles

- **Void Black** (`#0a0a0a`) — Primary background. The canvas all content floats on.
- **Lifted Surface** (`#111111`) — Card and panel fill. 1 step above void.
- **Raised Surface** (`#1a1a1a`) — Hover states, selected rows, active nav items.
- **Structural Edge** (`#262626`) — All 1px borders. Dividers. Table row separators.
- **Ghost Border** (`rgba(255,255,255,0.06)`) — Subtle inset shadows on card edges.
- **Ash Text** (`#f0f2f5`) — Primary text. Never pure white — optical warmth.
- **Slate Comment** (`#6b7280`) — Metadata, timestamps, labels, muted descriptions.
- **Deep Comment** (`#4b5563`) — Disabled states, placeholder text.
- **Indigo Pulse** (`#6366f1`) — Single accent. CTAs, active nav, focus rings, primary buttons. **No neon glow. No outer shadow.**
- **Indigo Tint** (`rgba(99,102,241,0.12)`) — Active nav background, selected state fills.
- **Emerald Signal** (`#10b981`) — Online status, clean scan results, success states.
- **Amber Alert** (`#f59e0b`) — Warning findings, medium severity, degraded states.
- **Crimson Flag** (`#ef4444`) — Critical findings, failed scans, error states, offline indicators.
- **Flame High** (`#f97316`) — High severity findings only.
- **Terminal Green** (`#4ade80`) — Live scan output text color inside dark terminal blocks.
- **Terminal Dim** (`#22c55e` at 60% opacity) — Completed tool output in terminal history.

**Banned:** Pure `#000000`. Neon purple glows. Oversaturated blue (`#0000ff`-adjacent). Any gradient on interactive components.

---

## 3. Typography Rules

- **UI Sans:** `Geist` — All dashboard chrome, navigation labels, stat values, table content, button text. Track-tight on headings (`-0.02em`), neutral on body (`0em`).
- **Display Numbers:** `Geist` weight 700 — Large stat counters (scan counts, finding totals). Tabular numerals (`font-variant-numeric: tabular-nums`).
- **Mono:** `JetBrains Mono` — Terminal output blocks, tool names, IP addresses, CVE IDs, timestamps, hash values, API keys (masked). All numbers inside dense data tables.
- **Banned:** `Inter` anywhere. `Times New Roman`, `Georgia`, `Garamond` absolutely. Serif fonts banned entirely — this is a security operations tool.

**Scale:**
- Page title: `20px / 600 weight / -0.02em tracking`
- Section heading: `14px / 600 weight / 0em tracking`
- Table header: `11px / 500 weight / 0.05em tracking / uppercase`
- Body / table content: `14px / 400 weight`
- Metadata / badges: `11–12px / 500 weight`
- Terminal output: `12px JetBrains Mono / 1.5 line-height`

**High-density override:** Any numeric value inside a data table uses `JetBrains Mono` at `12px`.

---

## 4. Hero Section (Dashboard Top)

The dashboard "hero" is a stats bar, not a marketing headline. Design rules:

- **4-column stat row** — not equal-weight. Critical findings column gets a red tint treatment when value > 0. All other columns are neutral.
- **No decorative icons as primary focus** — icons are `16px`, secondary to the number value.
- **Stat labels:** `11px / uppercase / 0.05em tracking / Slate Comment color`. The number speaks first.
- **"New Scan" CTA** anchored top-right, always visible. Indigo fill. `14px / 500 weight`. No secondary "Learn more" link next to it.
- **No taglines, no scroll prompts, no bouncing arrows.** The data is the headline.

---

## 5. Component Stylings

### Buttons
- **Primary:** Indigo Pulse fill (`#6366f1`), Ash Text label, `6px border-radius`, `8px 16px padding`. On `:active` — `-1px translateY` tactile push. No outer glow, no box-shadow.
- **Ghost / Secondary:** Transparent fill, Structural Edge border, Slate Comment text. On hover — Raised Surface fill.
- **Destructive:** Crimson Flag fill, same geometry as primary.
- **Disabled:** `opacity: 0.4`. No cursor change needed.
- **Icon Buttons:** `36px × 36px` minimum touch target. Ghost treatment.

### Navigation Sidebar
- `240px` fixed width. Lifted Surface background. Structural Edge right border.
- **Logo block:** Shield icon in Indigo Tint box (`28px × 28px`, `6px radius`). "CyberPulse" in `15px / 600 weight` Geist.
- **Nav items:** `14px / 500 weight`. `36px` row height. `6px` border-radius. Active state: Indigo Tint background + Indigo Pulse text color. Inactive: Slate Comment text → Ash Text on hover.
- **Section dividers:** `px-3` spacing only, no visible lines.
- **Bottom status block:** Kali VM connection indicator. `2px × 2px` colored dot (emerald/red/amber pulsing). `12px` Slate Comment label. Mono IP address below at `11px`.

### Cards / Stat Panels
- Lifted Surface background. `6px border-radius`. `1px` Structural Edge border.
- On hover: border transitions to `rgba(99,102,241,0.3)` — subtle indigo bleed, no shadow.
- Padding: `20px` all sides.
- **Never use box-shadow for elevation** — use border color shift instead.

### Data Tables
- Container: Lifted Surface background, `6px border-radius`, Structural Edge border.
- Header row: `48px height`. `11px / uppercase / 0.05em tracking` labels. `border-bottom` Structural Edge.
- Data rows: `48px height`. `border-bottom` Structural Edge (except last row). On hover: Raised Surface background.
- Row click: entire row is clickable — use `cursor: pointer` on `<tr>`.

### Status Badges (inline)
- No border outlines. Use tinted fill approach: `bg-color/10 text-color` pairing.
- **Running:** Blue tint + pulsing dot. **Completed:** Emerald tint. **Failed:** Crimson tint. **Pending:** Amber tint. **Analyzing:** Purple tint + pulsing dot.
- Geometry: `4px radius`, `6px 10px padding`, `11px / 500 weight`.

### Severity Badges
- **Critical (K):** `bg-red-500/10 text-red-400`
- **High (H):** `bg-orange-500/10 text-orange-400`
- **Medium (M):** `bg-yellow-500/10 text-yellow-400`
- **Low (L):** `bg-muted text-muted-foreground`
- **Info:** Ghost border treatment only.

### Scan Mode Badges
- **Blackbox:** `bg-red-400/10 text-red-400 border-red-400/20`
- **Graybox:** `bg-yellow-400/10 text-yellow-400 border-yellow-400/20`
- **Whitebox:** `bg-emerald-400/10 text-emerald-400 border-emerald-400/20`
- All use `1px` border, `4px radius`, `11px / 500 weight`.

### Terminal Blocks
- Background: `#0d1117` (GitHub dark, deeper than card surface).
- Text: `Terminal Green` (`#4ade80`) for active output. Dimmer green for completed history.
- Font: `JetBrains Mono 12px / 1.5 line-height`.
- Scrollbar: `4px` width, transparent track, `#262626` thumb.
- Container: `6px` radius, `1px` Structural Edge border. No glow.

### Phase Progress Sidebar (Scan Detail)
- Fixed left panel within scan detail view.
- Each phase: icon + label + status dot. `40px` row height.
- Active phase: Indigo Tint background. Completed: Emerald dot. Failed: Crimson dot. Pending: Ghost dot.
- Connecting line between phases: `1px` dashed Structural Edge.

### Connection Status Banner (Tools Page)
- Full-width, `6px radius`.
- **Online:** `border-emerald-500/30 bg-emerald-500/5 text-emerald-400`
- **Offline:** `border-red-500/30 bg-red-500/5 text-red-400`
- `14px` icon + label inline. IP in `JetBrains Mono`.

### Inputs / Forms
- Background: Lifted Surface. Border: Structural Edge. `6px radius`. `8px 12px padding`.
- On focus: `1px ring` in Indigo Pulse. No floating labels — label always above.
- Placeholder: Deep Comment color.
- Error: Crimson Flag text below input, `12px`. No red border flash.

### Loading States
- Skeletal shimmer blocks matching exact column/card dimensions.
- Shimmer color: animate between `#111111` and `#1a1a1a`.
- No circular spinners anywhere. The only spinner allowed is `Loader2` (Lucide) in inline `16px` usage when a single element is loading.

### Empty States
- Centered within container. Icon at `32–40px` opacity `20%`. One-line description in Slate Comment. Single CTA button below.
- Do not display empty tables — show the empty state composition instead.

---

## 6. Layout Principles

- **Grid-first:** CSS Grid for all multi-column layouts. No `calc()` flexbox hacks.
- **Page container:** `max-width: 1400px`, centered, `32px` side padding.
- **Dashboard grid:** Fixed `240px` sidebar + `1fr` main. `height: 100dvh` (not `h-screen`).
- **Main content padding:** `32px` all sides. Scrolls independently.
- **Stats row:** `grid-cols-4` with `16px gap`. Each cell equal width.
- **No overlapping elements.** Every element has its own clean spatial zone.
- **Section spacing:** `32px` vertical gap between major sections within a page.
- **Table container:** Full-width within main. Overflow scroll on mobile.
- **Scan detail:** Two-column split — `280px` phase sidebar + `1fr` terminal. Both scroll independently.
- **3-equal-column card grid is BANNED** — use 2-up asymmetric, 4-up, or full-width table instead.

**Mobile collapse (< 768px):**
- Sidebar collapses to bottom tab bar (5 icons, no labels).
- Stats row becomes 2×2 grid.
- Scan detail: phase sidebar stacks above terminal, collapses to accordion.
- All tables get horizontal scroll wrapper.
- Typography scales via `clamp()`.

---

## 7. Motion & Interaction

**Spring physics default:** `stiffness: 120, damping: 22` — weighty but not sluggish.

**Perpetual micro-loops:**
- Running scan status dots: CSS `animate-pulse` (2s ease-in-out infinite).
- Analyzing state dots: `animate-pulse` at 1.4s timing.
- Kali VM loading state: amber dot pulses until resolved.
- Skeletal shimmer: CSS `@keyframes shimmer` on `background-position` (hardware-accelerated).

**Staggered reveals:**
- Tool cards per phase: `stagger-delay: 30ms` per card, cascade from left-to-right.
- Phase list items in scan detail: `stagger-delay: 50ms` per phase on mount.
- Stats row on dashboard load: `stagger-delay: 80ms` per card.

**Interaction states:**
- Button active: `-1px translateY` + slight `scale(0.98)`. Duration `80ms`. No easing — snap.
- Row hover: `background-color` transitions at `150ms ease`.
- Nav item active: `background-color` at `120ms ease`. No sliding indicator bars.
- Modal/drawer open: `translateY(8px) opacity(0)` → `translateY(0) opacity(1)`. `200ms`. Spring easing.

**Performance rules:**
- Animate exclusively via `transform` and `opacity`.
- Never animate `height`, `top`, `left`, `width`.
- Grain/noise overlays: fixed `::before` pseudo-element, `pointer-events: none`, `z-index: -1`.
- Client Components isolated for all animation-heavy widgets.

---

## 8. Anti-Patterns — Strictly Banned

- **No `Inter` font** — use `Geist` for UI, `JetBrains Mono` for terminal/data.
- **No pure `#000000`** — use `#0a0a0a` (Void Black) minimum.
- **No neon/outer glow shadows** — `box-shadow: 0 0 20px rgba(99,102,241,0.5)` is explicitly banned.
- **No gradient text on headers** — no `bg-clip: text` on headings.
- **No 3-equal-column feature grids** — asymmetric or full-width only.
- **No emojis** anywhere in UI text.
- **No purple neon "AI aesthetic"** — indigo is used at low opacity for backgrounds only.
- **No overlapping elements** — clean spatial separation always enforced.
- **No custom mouse cursors.**
- **No centered hero sections** with taglines — this is a dashboard, not a landing page.
- **No "Elevate", "Seamless", "Unleash", "Next-Gen", "AI-Powered"** copywriting.
- **No generic placeholder names** ("John Doe", "Acme Corp", "testuser@email.com").
- **No fake round numbers** ("99.99% uptime", "500+ integrations").
- **No scroll-to-explore prompts, bouncing chevrons, or arrow scroll indicators.**
- **No broken image links** — use `picsum.photos/{id}` for any placeholder imagery.
- **No circular loading spinners** except inline `Loader2` at `16px`.
- **No toast notifications for destructive actions** — use inline confirmation dialogs.
- **No success toasts for background operations** — status is reflected in the data row itself.
- **No `h-screen`** — always `min-h-[100dvh]` for full-height sections (iOS Safari fix).
- **No floating labels** on form inputs — label always above the field.
- **No tab bar labels on mobile** — icons only, `44px` minimum touch target.

# XLOVEBEATS — CSS Architecture

## How It Works

Only **import files** are linked in HTML templates. Each import file loads its
sub-files via `@import`. This keeps templates clean and styles modular.

```
base.html → base-main.css  → base/reset.css
                            → base/auth.css
                            → ...

          → header-main.css → header.css
                            → account-modal.css
                            → ...

          → cart-main.css   → cart/base.css
                            → cart/items.css
                            → ...

index.html → home-main.css → home/hero.css
                            → home/tabs.css
                            → ...

admin/   → admin-main.css → admin/base.css
                            → admin/components.css
                            → ...
```

---

## Template Links

### base.html (all public pages)
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/base-main.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/header-main.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/cart-main.css') }}">
```

### index.html (homepage only)
```html
{% block head_css %}
    <link rel="stylesheet" href="{{ url_for('static', filename='css/home-main.css') }}">
{% endblock %}
```

### admin/base.html (admin panel)
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/admin-main.css') }}">
```

---

## File Map

### ── BASE (shared, every page) ──

| Import File | Sub-File | What It Does |
|-------------|----------|--------------|
| `base-main.css` | | Imports all base sub-files |
| | `base/reset.css` | CSS variables, reset, body, scrollbar, ambient gradient, floating notes, common animations, back button |
| | `base/auth.css` | Auth buttons in header (login/signup/ghost/primary), auth modal overlay, modal form, error states, submit button, switch link |
| | `base/user-sidebar.css` | User sidebar panel (slides from right), profile header, tabs (purchases/profile), purchase items, download buttons, profile rows, empty states |
| | `base/preloader.css` | Full-screen loading screen, spinning vinyl, equalizer bars, progress bar |
| | `base/mobile.css` | All responsive overrides at 700px — auth buttons collapse, user sidebar becomes bottom sheet, reduced motion |

### ── HEADER (shared, every page) ──

| Import File | Sub-File | What It Does |
|-------------|----------|--------------|
| `header-main.css` | | Imports all header sub-files |
| | `header.css` | Site header container (sticky), logo, desktop nav pill, nav links, active states, glow animations, divider, cart badge, account status dot, scroll state |
| | `account-modal.css` | Account button, modal overlay, modal panel (slides right), profile header, close button, tabs (products/licenses/settings), tab content, product items, license items, settings cards, guest states, logout button, mobile responsive |
| | `mobile-nav.css` | Mobile bottom nav (fixed), nav items, active states, account circle button, cart badge, toast system, mobile responsive |

### ── CART (shared, every page) ──

| Import File | Sub-File | What It Does |
|-------------|----------|--------------|
| `cart-main.css` | | Imports all cart sub-files |
| | `cart/base.css` | Cart overlay, drawer container (slides from right), ambient glow orb, cart header, spinning vinyl icon, waveform equalizer bars |
| | `cart/items.css` | Items scrollable area, individual cart items (enter/exit animations), thumbnail, name, type badges (pack/preset/single), license tag, price, remove button, empty state (floating vinyl), browse CTA, suggestion chips |
| | `cart/checkout.css` | Cart footer, summary rows (subtotal/discount/total), grand total gradient text, checkout button (shimmer hover effect), trust badges |
| | `cart/toast.css` | Toast notification system (fixed bottom center), toast enter/exit animations, success/error/info/warning variants, cart badge pop animation |
| | `cart/responsive.css` | Mobile cart (480px) — drawer becomes bottom sheet, smaller items, reduced motion preferences |

### ── HOME (index.html only) ──

| Import File | Sub-File | What It Does |
|-------------|----------|--------------|
| `home-main.css` | | Imports all homepage sub-files |
| | `home/hero.css` | Hero section (2-column grid), gradient title, slogan, CTA button, equalizer bars animation, hero visual (circular image with conic gradient border), section divider |
| | `home/tabs.css` | Main container, tab navigation (pill buttons), tab content visibility, trust strip (badges row) |
| | `home/cards.css` | Product grid, card styles, image wrapper, HOT/NEW badges, skeleton shimmer, hover zoom, genre tags, price, add-to-cart / buy-now buttons, scroll reveal animation, beats preview grid, beat cards with play button, view-all link |
| | `home/sections.css` | Testimonials section + grid + cards, producer credits, contact section, social grid + cards, WhatsApp floating button + tooltip |
| | `home/responsive.css` | All homepage responsive — 1024px (hero stacks), 700px (smaller hero/fonts/cards), 480px (smallest breakpoints) |

### ── ADMIN (admin panel only) ──

| Import File | Sub-File | What It Does |
|-------------|----------|--------------|
| `admin-main.css` | | Imports all admin sub-files |
| | `admin/base.css` | Admin variables, reset, layout (sidebar + main), sidebar (fixed 260px), nav items, main content area, header, flash messages |
| | `admin/components.css` | Stats grid, stat cards, dashboard grid, data tables, table images, status/type/action badges, buttons (primary/secondary/icon), action buttons |
| | `admin/forms.css` | Form container, form sections, form groups, inputs/selects/textareas, focus states, custom select dropdowns, file inputs, form layout, placeholders |
| | `admin/pages.css` | Page header, filter tabs, activity list + items, order/user detail pages, info grids, analytics grid + cards, pagination |

---

## Quick Reference — "Where is X?"

| Looking For | File |
|-------------|------|
| CSS variables (colors, fonts, spacing) | `base/reset.css` |
| Header background/blur | `header.css` → `.site-header` |
| Nav link active state | `header.css` → `.nav-link.active` |
| Cart drawer open/close | `cart/base.css` → `.cart-drawer.open` |
| Cart item remove animation | `cart/items.css` → `.cart-item.removing` |
| Toast notifications | `cart/toast.css` (also in `mobile-nav.css`) |
| Mobile bottom nav | `mobile-nav.css` |
| Account modal | `account-modal.css` |
| Login/signup modal | `base/auth.css` |
| User sidebar (purchases) | `base/user-sidebar.css` |
| Hero section | `home/hero.css` |
| Product cards | `home/cards.css` |
| Tab switching styles | `home/tabs.css` |
| WhatsApp button | `home/sections.css` |
| Preloader (loading screen) | `base/preloader.css` |
| Admin sidebar | `admin/base.css` |
| Admin tables | `admin/components.css` |
| Admin forms | `admin/forms.css` |
| Mobile responsive (global) | `base/mobile.css` |
| Mobile responsive (homepage) | `home/responsive.css` |
| Mobile responsive (cart) | `cart/responsive.css` |

---

## Full Directory Tree

```
static/css/
├── README.md                  ← You are here
│
├── base-main.css              ← Import: base/*
├── header-main.css            ← Import: header + account-modal + mobile-nav
├── cart-main.css              ← Import: cart/*
├── home-main.css              ← Import: home/*
├── admin-main.css             ← Import: admin/*
│
├── base/
│   ├── reset.css              ← Variables, reset, body, scrollbar, animations
│   ├── auth.css               ← Auth buttons, login/signup modals
│   ├── user-sidebar.css       ← User sidebar panel, purchases, profile
│   ├── preloader.css          ← Loading screen with vinyl + equalizer
│   └── mobile.css             ← Global mobile responsive (700px)
│
├── header.css                 ← Site header, desktop nav, logo, badge
├── account-modal.css          ← Account modal, tabs, products, settings
├── mobile-nav.css             ← Mobile bottom nav, toast duplicates
│
├── cart/
│   ├── base.css               ← Overlay, drawer, header, waveform
│   ├── items.css              ← Cart items, empty state, suggestions
│   ├── checkout.css           ← Footer, summary, checkout button
│   ├── toast.css              ← Toast system, badge animation
│   └── responsive.css         ← Mobile cart (480px), reduced motion
│
├── home/
│   ├── hero.css               ← Hero, CTA, equalizer, visual
│   ├── tabs.css               ← Container, tabs, trust strip
│   ├── cards.css              ← Grid, cards, beats preview, reveal
│   ├── sections.css           ← Testimonials, contact, social, WhatsApp
│   └── responsive.css         ← Homepage responsive (1024/700/480)
│
└── admin/
    ├── base.css               ← Variables, layout, sidebar, header, flash
    ├── components.css         ← Stats, tables, badges, buttons
    ├── forms.css              ← All form styles
    └── pages.css              ← Filters, activity, detail, analytics
```

---

## Rules

1. **Never edit import files directly** — only add/remove `@import` lines
2. **Each sub-file owns one concern** — if you change a card, go to `home/cards.css`
3. **Mobile overrides go in the responsive.css** of that section, not scattered
4. **Variables live in `base/reset.css`** — change a color there, it updates everywhere
5. **Admin has its own variables in `admin/base.css`** — they do not conflict with public site

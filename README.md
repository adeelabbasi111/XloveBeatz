# XLoveBeats

XLoveBeats is a Flask-based music storefront and digital distribution platform for beats, beat packs, vocal presets, and licensing. The project combines a public storefront, authenticated user dashboard, cart and checkout flow, admin product management, file upload handling, and automated license generation.

This README is intended to help a human developer or AI agent quickly understand the project structure, data model, runtime flow, and the role of each important file.

> Notes for navigation: generated runtime folders such as cache folders, virtual environments, and uploaded media are intentionally excluded from this guide. The app stores runtime data under the static data directories.

---

## 1. Project purpose

XLoveBeats allows users to:
- browse beats, beat packs, and vocal presets
- play preview audio and inspect beat metadata
- add items to a cart and proceed through checkout
- view their purchase history and download files
- receive generated license PDFs for purchased beats

Administrators can:
- manage products, prices, metadata, files, and licenses
- upload audio, preview clips, images, presets, and pack archives
- review orders and generated licenses
- configure site-level settings

---

## 2. Core technology stack

- Python 3
- Flask for web server and routing
- Flask-SQLAlchemy for database models
- Flask-WTF and CSRF protection
- Flask-Migrate for schema evolution
- Razorpay integration for payments (with a test bypass mode)
- ReportLab for PDF license generation
- Jinja2 templates for UI rendering
- pytest for automated tests

---

## 3. High-level application architecture

The app uses a standard Flask blueprint architecture:

1. [app.py](app.py) creates the Flask app using an app factory.
2. Blueprints in [blueprints](blueprints) define route groups for public pages, auth, cart, payments, dashboard, admin, and API endpoints.
3. [helpers/models.py](helpers/models.py) holds the SQLAlchemy data model.
4. [helpers/services.py](helpers/services.py) contains the main business logic and query helpers.
5. [helpers/utils.py](helpers/utils.py) contains validation, auth helpers, slug generation, and template helpers.
6. Templates in [templates](templates) render the UI.
7. Static assets in [static](static) provide CSS, JavaScript, and uploaded media.

---

## 4. Runtime flow

A typical request follows this path:

1. The browser requests a URL.
2. The Flask app routes it to the relevant blueprint.
3. The blueprint calls helper/service functions.
4. The service layer reads or writes to the database.
5. The route renders a Jinja template with the relevant data.
6. Front-end JavaScript in [static/js](static/js) handles modals, cart behavior, dashboard actions, player controls, and admin upload progress.

---

## 5. Top-level project structure

```text
Xlovebeats/
├── app.py
├── blueprints/
├── helpers/
├── instance/
├── services/
├── static/
├── templates/
├── tests.py
├── requirement.txt
├── Changes.txt
└── .gitignore
```

Excluded from this guide: cache folders, virtual environments, generated media folders, and local runtime state.

---

## 6. Root-level files

- [app.py](app.py) — Flask app factory and entry point. Initializes the app, registers all blueprints, configures database, CSRF, rate limiting, and error handlers.
- [.gitignore](.gitignore) — Prevents committing cache files, generated data, virtual environments, secrets, and editor-specific files.
- [requirement.txt](requirement.txt) — Python dependency list for the project.
- [tests.py](tests.py) — Pytest-based integration tests for key routes and auth flows.
- [Changes.txt](Changes.txt) — Change-log placeholder file.

---

## 7. Blueprints

### [blueprints/public.py](blueprints/public.py)
Responsible for public-facing routes such as the homepage, player page, beat detail page, and preset detail page. It pulls product data from the services layer and renders the storefront templates.

### [blueprints/auth.py](blueprints/auth.py)
Handles user authentication and account recovery. Includes signup, login, logout, password reset request, and password reset confirmation routes.

### [blueprints/cart.py](blueprints/cart.py)
Handles cart viewing and basic cart actions such as adding, removing, and clearing items. It is tied to the current user or guest session.

### [blueprints/payment.py](blueprints/payment.py)
Handles the checkout and payment lifecycle. It creates Razorpay orders, verifies payments, clears the cart after successful payment, generates license PDFs, and serves downloadable files for completed orders.

### [blueprints/dashboard.py](blueprints/dashboard.py)
Handles the authenticated dashboard experience. It renders the dashboard page and exposes APIs for their purchases, licenses, profile, password changes, and downloads.

### [blueprints/admin.py](blueprints/admin.py)
The main admin module. It manages product CRUD, admin-only dashboards, file storage helpers, audio preview trimming, pack ZIP generation, temporary file uploads, and order/license data views.

### [blueprints/api.py](blueprints/api.py)
Provides lightweight API endpoints for health checks, auth status, signup/login/logout, and user purchase history.

### [blueprints/__init__.py](blueprints/__init__.py)
Package initializer for the blueprint package.

---

## 8. Helpers and domain logic

### [helpers/config.py](helpers/config.py)
Stores configuration values for the app: secret key, database URI, upload paths, Razorpay credentials, rate limits, and pagination defaults.

### [helpers/models.py](helpers/models.py)
Defines the SQLAlchemy data model for users, products, beat packs, beat details, vocal presets, licenses, carts, orders, downloads, generated licenses, site settings, discount codes, and activity logs.

Key models:
- User — account and admin state
- Product — base product entity for beat, pack, or preset
- BeatPack — metadata for a beat pack
- BeatDetail — beat metadata and audio file references
- VocalPreset — preset metadata and archive path
- License — license tier definitions
- BeatLicensePrice — price tiers for beats by license type
- Cart and CartItem — temporary purchase selections
- Order and OrderItem — paid purchase state
- GeneratedLicense — stored PDF license documents
- Download — download tracking per user and product
- SiteSettings and DiscountCode — store configuration and discounts

### [helpers/services.py](helpers/services.py)
The service layer that encapsulates the main database and business logic. It is the bridge between routes and ORM code.

It handles:
- user creation and lookup
- homepage and player data selection
- beat detail enrichment
- cart and order creation
- download tracking
- admin statistics and reporting

### [helpers/utils.py](helpers/utils.py)
Utility layer for:
- slug generation
- price conversion and formatting
- auth decorators
- email sending for password resets
- input validation
- file upload helpers
- template filters

### [helpers/seed.py](helpers/seed.py)
Seeds basic initial data, including a default admin account when the application starts.

### [helpers/license_generator.py](helpers/license_generator.py)
Generates PDF beat licenses using ReportLab. It creates structured legal-style documents for basic, premium, and exclusive licenses.

### [helpers/__init__.py](helpers/__init__.py)
Package initializer for the helpers package.

---

## 9. Services layer

### [services/license_generator.py](services/license_generator.py)
A wrapper service around the license generator. It is used to create and persist license PDFs for order items.

---

## 10. Static assets

### JavaScript files

- [static/js/auth.js](static/js/auth.js) — handles auth modal toggling, account modal UI, login/signup flows, and user account state updates.
- [static/js/cart.js](static/js/cart.js) — powers the cart drawer, local cart state, add/remove actions, checkout flow, and toast messaging.
- [static/js/dashboard.js](static/js/dashboard.js) — handles dashboard tab switching, profile editing, and password updates.
- [static/js/index.js](static/js/index.js) — homepage interactions such as tab switching, scroll reveals, hero animation, and cart button delegation.
- [static/js/player.js](static/js/player.js) — the main beat player logic: audio playback, waveform rendering, visualizer, tracklist, volume control, and license selection.
- [static/js/admin.js](static/js/admin.js) — admin UI enhancements such as form field toggling, flash message dismissal, confirm dialogs, and slug previews.
- [static/js/trimmer.js](static/js/trimmer.js) — audio waveform trimmer UI for preview selection in the admin product form.
- [static/js/upload-progress.js](static/js/upload-progress.js) — uploads files immediately to temp storage and shows progress bars before the admin form is submitted.

### CSS files

- [static/css/style.css](static/css/style.css) — a general stylesheet entry point.
- [static/css/dashboard.css](static/css/dashboard.css) — dashboard-specific styling.

Base styles:
- [static/css/base/main.css](static/css/base/main.css) — shared layout and component styling.
- [static/css/base/resets.css](static/css/base/resets.css) — CSS resets and base normalization.
- [static/css/base/auth.css](static/css/base/auth.css) — authentication modal and form styling.
- [static/css/base/mobile.css](static/css/base/mobile.css) — responsive behavior for smaller screens.
- [static/css/base/preloader.css](static/css/base/preloader.css) — splash preloader visuals.
- [static/css/base/user-sidebar.css](static/css/base/user-sidebar.css) — styling for the user sidebar account panel.

Header styles:
- [static/css/header/header.css](static/css/header/header.css) — main header component styling.
- [static/css/header/main.css](static/css/header/main.css) — global header bundle.
- [static/css/header/mobile-nav.css](static/css/header/mobile-nav.css) — mobile navigation styling.
- [static/css/header/account-modal.css](static/css/header/account-modal.css) — account modal overlay visuals.

Home page styles:
- [static/css/home/main.css](static/css/home/main.css) — home page bundle.
- [static/css/home/hero.css](static/css/home/hero.css) — hero section styling.
- [static/css/home/cards.css](static/css/home/cards.css) — product cards and card layouts.
- [static/css/home/sections.css](static/css/home/sections.css) — section and content area styling.
- [static/css/home/mobile.css](static/css/home/mobile.css) — mobile home page adaptations.
- [static/css/home/tabs.css](static/css/home/tabs.css) — tab navigation styling.

Cart styles:
- [static/css/cart/base.css](static/css/cart/base.css) — cart shell styles.
- [static/css/cart/main.css](static/css/cart/main.css) — cart bundle.
- [static/css/cart/items.css](static/css/cart/items.css) — cart item row styling.
- [static/css/cart/checkout.css](static/css/cart/checkout.css) — checkout-related UI.
- [static/css/cart/mobile.css](static/css/cart/mobile.css) — mobile cart adaptation.
- [static/css/cart/toast.css](static/css/cart/toast.css) — toast notification visuals.

Player styles:
- [static/css/player/main.css](static/css/player/main.css) — player bundle.
- [static/css/player/layout.css](static/css/player/layout.css) — overall layout styling.
- [static/css/player/player-card.css](static/css/player/player-card.css) — player card presentation.
- [static/css/player/tracklist.css](static/css/player/tracklist.css) — tracklist panel styling.
- [static/css/player/waveform.css](static/css/player/waveform.css) — waveform visuals.
- [static/css/player/volume.css](static/css/player/volume.css) — volume popup and controls.
- [static/css/player/responsive.css](static/css/player/responsive.css) — responsive player styles.
- [static/css/player/license-modal.css](static/css/player/license-modal.css) — license selection modal styling.

Admin styles:
- [static/css/admin/main.css](static/css/admin/main.css) — admin bundle.
- [static/css/admin/base.css](static/css/admin/base.css) — shared admin layout.
- [static/css/admin/components.css](static/css/admin/components.css) — reusable admin UI components.
- [static/css/admin/forms.css](static/css/admin/forms.css) — admin form styling.
- [static/css/admin/pages.css](static/css/admin/pages.css) — page-specific admin styling.
- [static/css/admin/upload-progress.css](static/css/admin/upload-progress.css) — progress bar styling for the upload workflow.

### Architecture notes
- [static/css/Architecture.md](static/css/Architecture.md) — internal CSS architecture notes.

### Images
- [static/images/hero2.jpg](static/images/hero2.jpg) — homepage hero image.
- [static/images/signature.png](static/images/signature.png) — signature used in generated license PDFs.

---

## 11. Templates

Templates are the UI layer for the app and are rendered by the Flask routes.

### Core templates
- [templates/base.html](templates/base.html) — global base template that includes the header, auth modals, cart drawer, toast notifications, shared scripts, and page-specific blocks.
- [templates/index.html](templates/index.html) — homepage storefront showing beat packs, singles redirect, vocal presets, and marketing sections.
- [templates/player.html](templates/player.html) — beat player experience with audio controls, waveform, tracklist, and license modal.
- [templates/dashboard.html](templates/dashboard.html) — user account dashboard for purchases, licenses, orders, and settings.
- [templates/preset_detail.html](templates/preset_detail.html) — detail page for a vocal preset.
- [templates/payment_success.html](templates/payment_success.html) — post-payment success page.
- [templates/404.html](templates/404.html) — custom 404 page.

### Shared partials
- [templates/partials/header.html](templates/partials/header.html) — site header and navigation.
- [templates/partials/mobile_nav.html](templates/partials/mobile_nav.html) — mobile navigation component.
- [templates/partials/auth_modals.html](templates/partials/auth_modals.html) — login and signup modal UI.
- [templates/partials/user_sidebar.html](templates/partials/user_sidebar.html) — user account sidebar.
- [templates/partials/cart.html](templates/partials/cart.html) — cart drawer UI.
- [templates/partials/toast.html](templates/partials/toast.html) — toast container.
- [templates/partials/preloader.html](templates/partials/preloader.html) — preloader UI.
- [templates/partials/reset_password.html](templates/partials/reset_password.html) — password reset form UI.

### Admin templates
- [templates/admin/base.html](templates/admin/base.html) — admin layout shell.
- [templates/admin/dashboard.html](templates/admin/dashboard.html) — admin overview page.
- [templates/admin/products.html](templates/admin/products.html) — product listing.
- [templates/admin/product_form.html](templates/admin/product_form.html) — product create/edit form.
- [templates/admin/orders.html](templates/admin/orders.html) — order listing.
- [templates/admin/order_detail.html](templates/admin/order_detail.html) — order detail view.
- [templates/admin/users.html](templates/admin/users.html) — user management.
- [templates/admin/user_detail.html](templates/admin/user_detail.html) — single-user detail.
- [templates/admin/licenses.html](templates/admin/licenses.html) — generated and managed licenses.
- [templates/admin/discounts.html](templates/admin/discounts.html) — discount code management.
- [templates/admin/settings.html](templates/admin/settings.html) — site settings.
- [templates/admin/logs.html](templates/admin/logs.html) — activity log view.
- [templates/admin/analytics.html](templates/admin/analytics.html) — analytics overview.

---

## 12. Important application workflows

### Public browsing
The public experience routes in [blueprints/public.py](blueprints/public.py) load beat packs, beats, and presets and render them on the homepage and player page.

### Authentication
Auth routes in [blueprints/auth.py](blueprints/auth.py) and [blueprints/api.py](blueprints/api.py) handle signup, login, logout, and reset flows. Session state is tied to the user ID.

### Cart and checkout
The cart system is managed by [blueprints/cart.py](blueprints/cart.py) and [static/js/cart.js](static/js/cart.js). The server stores cart rows in the database and the client keeps a lightweight local cart state for the UI.

### Payment and licenses
The payment workflow in [blueprints/payment.py](blueprints/payment.py) creates orders, verifies payment, clears carts, and generates license PDFs. Files are saved under the data directory and linked from the generated license records.

### Admin product management
The admin blueprint in [blueprints/admin.py](blueprints/admin.py) handles file uploads, audio preview generation, pack zip generation, and CRUD management of products and related entities.

### File storage conventions
Runtime file storage is expected under the application’s data directories. These are used for:
- previews
- mp3 files
- wav files
- flp files
- images
- presets
- packs
- licenses

These are managed by the admin routes and referenced in the database via relative paths.

---

## 13. Database model summary

The app is centered around a product catalog and commerce workflow:
- Products are the core catalog entities.
- Beat packs group one or more beats.
- Beat details attach metadata and media to a beat.
- Vocal presets are treated as separate digital products.
- Orders capture purchases.
- Generated licenses are linked to paid order items.
- Downloads track user access to purchased items.

---

## 14. Local development notes

To run the project locally:

```bash
pip install -r requirement.txt
python app.py
```

The app uses SQLite by default and stores the database at [instance](instance) as the local application database file.

---

## 15. Testing

The project includes basic pytest coverage in [tests.py](tests.py). It checks health endpoints, public page access, auth behaviors, cart behavior, admin protection, and the API auth endpoints.

---

## 16. Recommended starting points for an AI agent

If you are trying to understand or extend this app, start in this order:

1. [app.py](app.py) — app startup and blueprint registration
2. [helpers/models.py](helpers/models.py) — the schema and business entities
3. [helpers/services.py](helpers/services.py) — main business logic
4. [blueprints/public.py](blueprints/public.py) — public user flows
5. [blueprints/payment.py](blueprints/payment.py) — purchase and licensing flow
6. [blueprints/admin.py](blueprints/admin.py) — content management flow
7. [templates/base.html](templates/base.html) and [templates/index.html](templates/index.html) — base UI structure
8. [static/js/player.js](static/js/player.js) and [static/js/cart.js](static/js/cart.js) — main interactive behaviors

---

## 17. Summary

This repository is a full-featured Flask storefront for a beat marketplace. It combines:
- content management
- ecommerce
- user accounts
- media storage
- licensing automation
- admin reporting
- interactive frontend UI

The project is organized around a clear separation between routes, services, models, templates, and static assets, making it relatively straightforward to extend or debug.

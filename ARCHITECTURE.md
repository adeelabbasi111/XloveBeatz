# Xlovebeats Project Architecture

This document provides a comprehensive overview of the Xlovebeats project structure. It explains the purpose of every major folder and file in the codebase.

## 📂 Root Directory
The root folder contains the core entry points and configuration files required to run the application.

- **`app.py`**: The Application Factory. This is the heart of the Flask app where extensions (database, login, rate limiting) are initialized and all blueprints (routes) are registered.
- **`wsgi.py`**: The Production Entry Point. Used by production web servers (like Gunicorn or Waitress) to serve the app to multiple users concurrently.
- **`.env.example`**: A template for environment variables (API keys, database URIs, secret keys).
- **`requirements.txt`**: The list of all Python dependencies required to run the app (install using `pip install -r requirements.txt`).
- **`instance/`**: Contains instance-specific files, most notably your SQLite database (`app.db`).

---

## 📂 `blueprints/` (The Controllers)
This folder contains the routing logic. Flask "Blueprints" allow us to split a large application into smaller, manageable files based on features.

- **`admin.py`**: Handles all routes for the admin panel (`/admin/...`). Responsible for uploading beats, managing users, and viewing analytics.
- **`api.py`**: Contains JSON endpoints, often used by the frontend JavaScript to fetch data asynchronously without reloading the page.
- **`auth.py`**: Handles user authentication (login, registration, password resets).
- **`cart.py`**: Manages the shopping cart functionality (adding/removing items, session storage).
- **`dashboard.py`**: Handles the customer dashboard (`/dashboard/...`) where users can view their past purchases and download files.
- **`payment.py`**: Integrates with Cashfree (or other payment gateways) to process checkout, webhooks, and order verification.
- **`public.py`**: Handles public-facing static pages (e.g., Home, About, Contact).

---

## 📂 `helpers/` (The Engine)
This folder contains the core business logic, database definitions, and utility functions that power the blueprints.

- **`config.py`**: Defines the `Config` class, which loads environment variables and sets up Flask configurations (like upload limits and session lifetimes).
- **`models.py`**: The Database Schema. Defines all SQLAlchemy models (e.g., `User`, `Product`, `Order`) and how they relate to each other.
- **`services.py`**: Contains complex business logic and third-party integrations, keeping the blueprint files clean and focused strictly on routing.
- **`utils.py`**: Helper functions (e.g., file validation, string formatting, sending emails).
- **`seed.py`**: A script that runs on the first launch to populate the database with default data (like default license types).

---

## 📂 `static/` (Frontend Assets)
This folder contains all the files that are sent directly to the user's browser.

- **`css/`**: Contains the stylesheets. 
  - *Note: We utilize a bundled architecture (`home-bundle.css`, `player-bundle.css`) to minimize HTTP requests and speed up page loads.*
- **`js/`**: Contains the client-side JavaScript.
  - `player.js`: The custom audio player logic.
  - `cart.js`: Handles cart interactions.
  - `waveform-generator.js`: Generates visual waveforms for beats.
- **`images/`**: Static site images (logos, hero backgrounds, placeholders).
- **`data/`**: The dynamic storage folder. This is where user-uploaded files are saved (e.g., `mp3/`, `wav/`, `beat_images/`, `packs/`). **This folder must be backed up regularly.**

---

## 📂 `templates/` (The Views)
This folder contains the Jinja2 HTML templates that dictate the visual layout of the site.

- **`base.html`**: The master template. It contains the `<head>`, includes the CSS/JS, and defines the overall structure that every other page inherits.
- **`index.html`**: The Homepage template.
- **`about.html`**, **`player.html`**, **`product_detail.html`**: Specific page layouts.
- **`admin/`**: Contains all the HTML files specifically for the Admin Dashboard (e.g., `dashboard.html`, `products.html`).
- **`partials/`**: Reusable HTML components.
  - `header.html`: The navigation bar.
  - `footer.html`: The site footer.
  - `auth_modals.html`: The popup windows for login/registration.
  - `cart.html`: The slide-out cart menu.

---

## 📂 `scripts/` (DevOps & Ops)
Standalone Python scripts used for server maintenance and operations.

- **`backup.py`**: An automated script that creates timestamped backups of your SQLite database (`app.db`) to ensure data safety.

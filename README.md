# Gatepass — Ticketing Platform Backend

Gatepass is a backend system for a full-featured ticketing platform. Organizers can create events and sell tickets, attendees get cryptographically signed QR codes for entry, and a built-in marketplace allows ticket reselling.

---

## Why Gatepass?

Most ticketing backends are just CRUD. Gatepass adds a security layer at the core: every ticket is generated with a **signed QR code** that can be verified at the door. Duplicated or screenshot tickets fail verification — the signature won't match. This makes forgery practically impossible without access to the signing key.

---

## Features

- **Event Management** — Organizers can create and manage events with full details
- **Ticket Sales** — Attendees can purchase tickets tied to specific events
- **Signed QR Codes** — Each ticket carries a cryptographic signature for anti-forgery verification
- **QR Scanning & Admission** — Scan tickets at the door; invalid or duplicate tickets are rejected
- **Resale Marketplace** — Users can list and purchase secondhand tickets with ownership transfer handled securely

---

## Tech Stack

| Tool | Purpose |
|---|---|
| **Python** | Primary language |
| **Django** | Web framework |
| **Django REST Framework** | API layer |
| **PostgreSQL / SQLite** | Database |

---

## Project Structure

```
Gatepass/
├── accounts/        # User registration, authentication
├── events/          # Event creation and management
├── tickets/         # Ticket generation, QR signing, admission
├── marketplace/     # Ticket resale logic
└── TicketApp/       # Project settings and config
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/Im-Kaycee/TicketApp.git
cd TicketApp
```

2. **Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Run migrations**

```bash
python manage.py migrate
```

5. **Start the server**

```bash
python manage.py runserver
```

---

## How Ticket Verification Works

When a ticket is purchased, the backend generates a QR code containing the ticket data and signs it with a private key. At the event entrance, scanning the QR code triggers a verification check — the signature is validated server-side. If the ticket has already been scanned, been tampered with, or is a copy, admission is denied.

---



## Related

Built as the backend for the **Gatepass** platform. Frontend available at https://github.com/Im-Kaycee/gatepass-web

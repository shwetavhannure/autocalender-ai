# AutoCalendar AI: Autonomous Email-to-Calendar Assistant

An intelligent, background worker system that scans incoming emails, extracts deadline and event metadata using LLMs, and automatically schedules structured events directly into Google Calendar.

---

## Key Features

- **LLM Event Extraction:** Leverages OpenRouter AI inference with dynamic time-context injection and few-shot prompts to parse relative dates (*"this Friday"*, *"17th of this month"*) into strict ISO-8601 timestamps.
- **Idempotent Background Worker:** Asynchronous worker loop in Python polling active mailboxes with duplicate-message filtering powered by MongoDB tracking.
- **Contextual Event Titling:** Automatically maps email subjects, course names, and body text into descriptive event titles (e.g., *CS-302 Midterm Exam* instead of generic titles like *Exam*).
- **Multi-User OAuth2 Architecture:** Secure token storage and handling via MongoDB for seamless multi-user calendar synchronization.
- **Junk & Non-Event Filtering:** Intelligent pre-filtering via keyword lists and LLM classification to ignore promotional content, receipts, and general newsletters.

---

## 📸 Demo & Screenshots

### 1. Landing Page & OAuth Trigger
The app checks for an active Google Workspace connection on load.

<img src="docs/images/login-screen.png" width="700" alt="AI Deadline Auto-Pilot login screen">

### 2. Google OAuth2 Authentication
Secure, standard OAuth 2.0 consent flow — no credentials are stored outside the encrypted token store.

<img src="docs/images/successfull-auth.png" width="700" alt="OAuth authentication success screen">

### 3. Background Worker in Action
The polling worker fetches unread mail, runs LLM extraction, and syncs directly to Google Calendar — fully autonomous, no manual intervention.

<img src="docs/images/console-logs-worker.png" width="700" alt="Terminal output of background worker processing emails">

### 4. Auto-Generated Calendar Events
Each event is tagged with its source context, extracted venue, and default reminders — no manual data entry required.

| Mess Registration Event | Assignment Deadline Event |
| :---: | :---: |
| <img src="docs/images/calendar-result-1.png" width="380"> | <img src="docs/images/calendar-result-2.png" width="380"> |

---

## System Architecture & Data Flow

```text
[ Gmail API ] ──( Fetch Unread )──> [ Background Worker ]
                                           │
                                  ( Subject + Body )
                                           ▼
                                  [ Parser Engine ]
                                           │
                                    ( OpenRouter LLM )
                                           ▼
[ Google Calendar ] <──( Inject Event )── [ Extracted Metadata ] ──( Log ID )──> [ MongoDB ]
```

1. **Ingestion:** Worker fetches unread emails via the Gmail REST API.
2. **Filtering:** Checks processing history in MongoDB to prevent duplicate runs.
3. **Extraction:** ParserEngine formats context and sends requests to the LLM.
4. **Injection:** Parsed events are normalized and added to Google Calendar.
5. **State Update:** MongoDB records `email_id` to enforce strict idempotency.

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| Language | Python 3.10+ | Core application logic and pipeline runtime |
| Database | MongoDB | User state, OAuth token storage, idempotency history |
| AI Inference | OpenRouter / Hugging Face | Natural language extraction of unstructured dates/titles |
| External APIs | Gmail API, Google Calendar API | Mail ingestion and calendar event injection |
| Authentication | Google OAuth 2.0 | Multi-user credential delegation |

---

## Project Structure

```text
autocalendar-ai/
├── config/
│   └── settings.py          # Environment variables & system defaults
├── src/
│   ├── calendar_engine.py   # Google Calendar API integration
│   ├── database_mgr.py      # MongoDB CRUD & user state management
│   ├── gmail_engine.py      # Gmail REST API mailbox polling
│   ├── parser_engine.py     # LLM inference & prompt construction
│   ├── utils.py             # Date normalization & output cleaning
│   └── worker.py            # Main background polling process
├── .env.example              # Template for required environment variables
├── requirements.txt          # Project dependencies
└── README.md                 # Project documentation
```

---

## 🚀 Local Setup Instructions

### 1. Prerequisites

- Python 3.10 or higher
- MongoDB instance (Local or MongoDB Atlas)
- Google Cloud Console Project with Gmail & Calendar APIs enabled

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/omkhot/AutoCalendar-AI.git
cd autocalendar-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Setup

Create a `.env` file in the root directory:

```env
HF_TOKEN=your_openrouter_or_hf_token
MONGO_URI=mongodb://localhost:27017/
DB_NAME=autocalendar_db
POLLING_INTERVAL_SECONDS=300
```

### 4. Running the Application

```bash
# Start the background polling worker
python -m src.worker
```

---

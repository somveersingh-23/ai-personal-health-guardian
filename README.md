# 🩺 AI Personal Health Guardian

> **A privacy-first AI-powered personal health intelligence mobile application**

---

## 📌 Project Overview

AI Personal Health Guardian is a **mobile-first health intelligence system** that collects consented health-related signals, learns the user's **personal health baseline**, detects meaningful deviations, and provides **explainable, safety-controlled insights**.

The system is designed around three core capabilities:

1. **SENSE** → collect and process health signals
2. **UNDERSTAND** → learn the user's personal baseline and detect meaningful changes
3. **GUARD** → explain changes and provide safe, appropriate actions

### Example

Instead of simply saying:

> Heart rate = 88 BPM

the system should understand the user's normal pattern:

```text
Personal baseline:
Resting HR = 65–75 BPM

Today's HR:
88 BPM

Other signals:
Sleep ↓
HRV ↓
Activity ↓

        ↓

Meaningful deviation detected

        ↓

AI Guardian explains the change
```

> ⚠️ **Important:** This project is a health-intelligence/research prototype, not a medical diagnosis system. The AI must not claim that a user definitely has a disease. Clinical confirmation may require professional evaluation, laboratory tests, imaging, or other appropriate medical procedures.

---

# 🎯 Project Vision

The long-term vision is a system that can privately understand:

> **"What is normal for this person?"**

and notice:

> **"Something is meaningfully different today."**

The system can then provide an understandable explanation and, when appropriate, trigger a safety-controlled action.

---

# 👥 TEAM STRUCTURE

There are **3 members**.

All three members are full-stack developers with experience/interests in:

- Mobile development
- Frontend
- Backend
- Databases
- ML
- AI/LLM

Therefore, we will **NOT** divide the team into:

```text
Member 1 = Frontend
Member 2 = Backend
Member 3 = ML
```

Instead, every member works across the technology stack.

Each member has one **primary module**.

---

## 👨‍💻 MEMBER 1 — PERSONAL HEALTH DIGITAL TWIN

### Main responsibility

> **Understand what is normal for the user.**

### Main question

> "What is normal for this particular person?"

### Mobile

- User profile
- Health profile
- Health dashboard
- Health timeline
- Personal baseline visualization

### Backend

- User APIs
- Health profile APIs
- Health event APIs
- Baseline APIs
- Timeline APIs

### Database

- Users
- Health profiles
- Health events
- Personal baselines
- Health timeline

### ML

- Data preprocessing
- Personal baseline calculation
- Trend analysis
- Anomaly detection
- Deviation scoring

### Main folders

```text
mobile/android/.../feature/profile/
mobile/android/.../feature/dashboard/
mobile/android/.../feature/timeline/

backend/app/api/baseline.py
backend/app/services/baseline/

ml/baseline/
```

---

# 👨‍💻 MEMBER 2 — MULTIMODAL SENSOR INTELLIGENCE

### Main responsibility

> **Collect and understand health signals.**

### Main question

> "What are the different health signals telling us together?"

### Mobile

- Android Health Connect
- Wearable integration
- Sensor permissions
- Device connection
- Sensor synchronization
- Camera capture prototype

### Backend

- Sensor APIs
- Device APIs
- Health-data ingestion
- Health-event pipeline
- Signal-quality APIs

### ML

- Signal quality
- Motion/noise handling
- Sensor fusion
- Multimodal health features
- Camera/image-quality prototype

### Main folders

```text
mobile/android/.../feature/sensors/

backend/app/api/sensors.py
backend/app/services/sensors/

ml/signal_quality/
ml/sensor_fusion/
```

---

# 👨‍💻 MEMBER 3 — AI GUARDIAN + SAFETY ENGINE

### Main responsibility

> **Explain detected changes and respond safely.**

### Main question

> "What should we tell the user and what should happen next?"

### Mobile

- AI chat
- Health insights
- Notifications
- Alert screen
- Emergency/caregiver UI

### Backend

- AI assistant APIs
- Insight APIs
- Alert APIs
- Safety APIs
- Notification APIs

### AI

- LLM integration
- RAG
- Health-information retrieval
- Evidence-based explanation
- Safety orchestration

### ML / Rules

- Safety rules
- Confidence handling
- Alert thresholds
- Re-measurement workflow

### Main folders

```text
mobile/android/.../feature/assistant/
mobile/android/.../feature/alerts/

backend/app/api/assistant.py
backend/app/api/alerts.py
backend/app/services/guardian/

ai/assistant/
ai/rag/
ai/prompts/

ml/safety/
```

---

# 🏗️ COMPLETE SYSTEM ARCHITECTURE

```text
                         ┌──────────────────────────┐
                         │      ANDROID APP         │
                         │ Kotlin + Jetpack Compose │
                         └────────────┬─────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
              User Profile      Health Connect      Camera
                                      │
                                  Wearables
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      ▼
                         ┌──────────────────────────┐
                         │    DATA INGESTION        │
                         │        FastAPI           │
                         └────────────┬─────────────┘
                                      ▼
                         ┌──────────────────────────┐
                         │       PostgreSQL         │
                         │     Health Event Store   │
                         └────────────┬─────────────┘
                                      ▼
                         ┌──────────────────────────┐
                         │  SIGNAL QUALITY ENGINE   │
                         └────────────┬─────────────┘
                                      ▼
                         ┌──────────────────────────┐
                         │ PERSONAL BASELINE ENGINE │
                         └────────────┬─────────────┘
                                      ▼
                         ┌──────────────────────────┐
                         │   SENSOR FUSION ENGINE   │
                         └────────────┬─────────────┘
                                      ▼
                         ┌──────────────────────────┐
                         │      SAFETY ENGINE       │
                         └────────────┬─────────────┘
                                      ▼
                         ┌──────────────────────────┐
                         │       AI GUARDIAN        │
                         │       LLM + RAG          │
                         └────────────┬─────────────┘
                                      │
                         ┌────────────┼────────────┐
                         ▼            ▼            ▼
                    Dashboard       AI Chat       Alert
```

---

# 🧱 REPOSITORY STRUCTURE

We use **ONE GitHub repository for the ENTIRE PROJECT**.

Repository name:

```text
ai-personal-health-guardian
```

Recommended structure:

```text
ai-personal-health-guardian/
│
├── mobile/
│   └── android/
│       ├── app/
│       ├── build.gradle.kts
│       ├── settings.gradle.kts
│       └── ...
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── health.py
│   │   │   ├── sensors.py
│   │   │   ├── baseline.py
│   │   │   ├── assistant.py
│   │   │   └── alerts.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── baseline/
│   │   │   ├── sensors/
│   │   │   └── guardian/
│   │   ├── database/
│   │   └── core/
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── ml/
│   ├── baseline/
│   │   ├── preprocessing/
│   │   ├── models/
│   │   └── notebooks/
│   │
│   ├── sensor_fusion/
│   ├── signal_quality/
│   └── safety/
│
├── ai/
│   ├── assistant/
│   ├── rag/
│   ├── prompts/
│   └── knowledge_base/
│
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── database/
│   └── research/
│
├── scripts/
│
├── .gitignore
├── .env.example
├── README.md
└── docker-compose.yml
```

---

# 📱 MOBILE ARCHITECTURE

The main product is an **Android mobile application**.

Recommended stack:

```text
Kotlin
Jetpack Compose
MVVM
Kotlin Coroutines
Retrofit
Room
Health Connect
```

Recommended Android structure:

```text
mobile/android/
└── app/
    └── src/main/java/
        └── ...
            ├── core/
            ├── data/
            ├── domain/
            └── feature/
                ├── auth/
                ├── profile/
                ├── dashboard/
                ├── timeline/
                ├── sensors/
                ├── assistant/
                └── alerts/
```

### Feature ownership

```text
Member 1
├── profile/
├── dashboard/
└── timeline/

Member 2
└── sensors/

Member 3
├── assistant/
└── alerts/
```

Ownership does NOT mean other members are forbidden from modifying these folders. It means the named member is primarily responsible for them.

---

# 🖥️ BACKEND ARCHITECTURE

Recommended:

```text
Python
FastAPI
PostgreSQL
SQLAlchemy
Pydantic
Docker
JWT Authentication
```

Backend:

```text
backend/
└── app/
    ├── api/
    ├── models/
    ├── schemas/
    ├── services/
    ├── database/
    └── core/
```

### API ownership

```text
Member 1
├── users.py
├── health.py
└── baseline.py

Member 2
└── sensors.py

Member 3
├── assistant.py
└── alerts.py
```

---

# 🗄️ DATABASE

We use **ONE PostgreSQL database**.

Initial conceptual schema:

```text
User
 │
 ├── HealthProfile
 │
 ├── HealthEvent
 │
 ├── Baseline
 │
 ├── SensorData
 │
 ├── HealthInsight
 │
 ├── Alert
 │
 └── Conversation
```

Possible tables:

```text
users
health_profiles
health_events
baselines
sensor_data
health_insights
alerts
conversations
consents
```

No member should create a separate database for their module.

---

# 🔄 COMMON HEALTH EVENT FORMAT

All health measurements should use a common structure.

Example:

```json
{
  "user_id": "123",
  "metric": "heart_rate",
  "value": 82,
  "unit": "bpm",
  "timestamp": "2026-08-27T10:30:00",
  "source": "health_connect",
  "quality": 0.95
}
```

Possible metrics:

```text
heart_rate
hrv
sleep
spo2
temperature
activity
steps
respiration
```

This common format allows all modules to communicate without depending on a specific device.

---

# 🧠 BASELINE RESULT FORMAT

Member 1's baseline/anomaly service should return structured data.

Example:

```json
{
  "metric": "heart_rate",
  "baseline": 72,
  "current": 88,
  "deviation_score": 2.1,
  "status": "above_normal"
}
```

Possible statuses:

```text
normal
below_normal
above_normal
unknown
```

---

# 🤖 AI INSIGHT FORMAT

The AI Guardian should consume structured evidence.

Example:

```json
{
  "type": "recovery",
  "severity": "moderate",
  "title": "Recovery is lower than usual",
  "evidence": [
    "Sleep decreased",
    "HRV decreased",
    "Resting HR increased"
  ]
}
```

The LLM should explain these results instead of independently making medical diagnoses.

---

# 🔐 PRIVACY AND SECURITY

Health data is sensitive.

We follow:

```text
User Consent
     ↓
Minimum Required Data
     ↓
Secure Transfer
     ↓
Protected Storage
     ↓
Controlled Processing
```

Rules:

- Ask permission before accessing health data.
- Collect only required information.
- Do not expose health data unnecessarily.
- Do not put API keys in GitHub.
- Do not commit `.env`.
- Use secure authentication.
- Protect database credentials.
- Provide user control over health data.
- Prefer on-device processing where practical.

---

# 🚨 SAFETY PRINCIPLE

The LLM must NOT independently determine medical emergencies.

Correct architecture:

```text
Health Data
    ↓
Signal Quality
    ↓
ML / Validated Logic
    ↓
Safety Rules
    ↓
Confidence
    ↓
Action
    ↓
LLM Explanation
```

Possible actions:

```text
NORMAL
   ↓
OBSERVE
   ↓
RE-MEASURE
   ↓
SELF-CARE GUIDANCE
   ↓
CAREGIVER ALERT
   ↓
EMERGENCY ESCALATION
```

The project is not a replacement for professional medical care.

---

# 🌳 GIT BRANCH STRATEGY

We use:

```text
main
  │
  └── develop
       │
       ├── feature/m1-...
       ├── feature/m2-...
       └── feature/m3-...
```

## `main`

Stable, tested project.

**Never directly develop on `main`.**

## `develop`

Combined development branch.

Completed features are merged here.

## Feature branches

Every task gets a separate branch.

Examples:

```text
feature/m1-health-profile
feature/m1-baseline-api
feature/m1-anomaly-detection

feature/m2-health-connect
feature/m2-sensor-ingestion
feature/m2-sensor-fusion

feature/m3-ai-chat
feature/m3-rag
feature/m3-safety-engine
```

---

# ❌ DO NOT CREATE PERMANENT MEMBER BRANCHES

Do NOT use:

```text
member1
member2
member3
```

for months.

Use:

```text
feature/m1-health-profile
feature/m1-baseline
feature/m2-health-connect
feature/m3-ai-chat
```

Each branch should represent **one feature/task**.

---

# 🔀 STANDARD GIT WORKFLOW

Every member follows the same workflow.

## STEP 1 — Update develop

```bash
git checkout develop
git pull origin develop
```

## STEP 2 — Create a feature branch

Example:

```bash
git checkout -b feature/m1-health-profile
```

## STEP 3 — Work on the feature

Write code, test it, and make small commits.

## STEP 4 — Check changes

```bash
git status
```

## STEP 5 — Stage

```bash
git add .
```

## STEP 6 — Commit

```bash
git commit -m "feat: add health profile"
```

## STEP 7 — Push

```bash
git push -u origin feature/m1-health-profile
```

## STEP 8 — Create Pull Request

Create:

```text
feature/m1-health-profile
              ↓
           develop
```

## STEP 9 — Code review

At least **one teammate** should review normal features.

Important architecture/security changes should ideally receive **two reviews**.

## STEP 10 — Merge

After approval:

```text
feature branch
      ↓
   develop
```

---

# 🔄 AFTER A FEATURE IS MERGED

Update your local branch:

```bash
git checkout develop
git pull origin develop
```

When starting your next task:

```bash
git checkout -b feature/next-task
```

---

# ⚠️ IF DEVELOP CHANGES WHILE YOU ARE WORKING

Suppose you are working on:

```text
feature/m1-baseline
```

and another member merges code into `develop`.

Before finishing your PR:

```bash
git checkout develop
git pull origin develop

git checkout feature/m1-baseline
git merge develop
```

Resolve conflicts if required.

Then:

```bash
git add .
git commit -m "chore: resolve merge conflicts"
git push
```

---

# 🚫 GITHUB RULES

## Rule 1

Never directly push normal development work to `main`.

## Rule 2

Never commit API keys.

## Rule 3

Never commit `.env`.

## Rule 4

Never commit passwords.

## Rule 5

Do not overwrite another member's work.

## Rule 6

Create a feature branch for each task.

## Rule 7

Test before creating a Pull Request.

## Rule 8

Keep commits small and meaningful.

## Rule 9

Pull latest `develop` before starting new work.

## Rule 10

Do not merge broken code into `develop`.

---

# 🔑 ENVIRONMENT VARIABLES

Create:

```text
.env
```

locally.

Never commit it.

Commit:

```text
.env.example
```

Example:

```text
DATABASE_URL=
SECRET_KEY=
AI_API_KEY=
```

No real credentials should be placed in this file.

`.gitignore` must contain:

```text
.env
.venv/
__pycache__/
*.pyc
.gradle/
.idea/
build/
local.properties
node_modules/
*.log
```

---

# 📝 COMMIT MESSAGE FORMAT

Use simple conventional commit messages.

### New feature

```text
feat: add health profile
```

### Bug fix

```text
fix: validate heart rate input
```

### Documentation

```text
docs: update architecture
```

### Refactoring

```text
refactor: simplify baseline service
```

### Configuration

```text
chore: update docker configuration
```

Avoid commits like:

```text
final
update
changes
new code
working
```

---

# 📋 GITHUB ISSUES

All significant tasks should be tracked using GitHub Issues.

Example:

## Issue

```text
Title:
Implement Personal Health Profile
```

Description:

```text
Create health profile screen.

Requirements:
- Basic user information
- Health information
- Allergies
- Medicines
- Save profile
- Update profile
- Connect with backend API
```

Assign the issue to Member 1.

Member 1 creates:

```text
feature/m1-health-profile
```

---

# 📊 GITHUB PROJECT BOARD

Recommended board:

```text
BACKLOG
   ↓
TODO
   ↓
IN PROGRESS
   ↓
CODE REVIEW
   ↓
TESTING
   ↓
DONE
```

Example:

```text
BACKLOG
├── BLE integration
└── Camera improvement

TODO
├── Health profile
└── Database schema

IN PROGRESS
├── Health Connect
└── Baseline model

CODE REVIEW
└── Authentication API

TESTING
└── AI Assistant

DONE
└── Android project setup
```

---

# 🔌 API CONTRACTS

Before heavy development starts, the three members must agree on the common API/data formats.

This is one of the most important team rules.

Example:

```text
Member 2
   ↓
Health Event
   ↓
Backend
   ↓
Member 1
   ↓
Baseline
   ↓
Member 3
   ↓
AI Guardian
```

If the API format changes, inform the whole team before making breaking changes.

---

# 🧪 TESTING

Every member is responsible for testing their own code.

## Mobile

Test:

- UI
- Navigation
- Permissions
- API calls
- Error states

## Backend

Test:

- API endpoints
- Validation
- Authentication
- Database operations
- Error handling

## ML

Test:

- Input data
- Model output
- Edge cases
- False positives
- Missing data

## AI

Test:

- Prompt behavior
- Retrieval
- Unsupported questions
- Safety behavior
- Hallucination handling

---

# 🚀 DEVELOPMENT ROADMAP

## PHASE 1 — FOUNDATION

### Weeks 1–2

All members work together.

Build:

- GitHub repository
- Android project
- FastAPI project
- PostgreSQL
- Docker
- Authentication
- Basic navigation
- Database structure
- API structure
- Initial UI

### Output

```text
Mobile → Backend → Database
```

must work.

---

# PHASE 2 — SIMULATED HEALTH DATA

### Weeks 3–4

Do not wait for physical wearable hardware.

Create simulated:

```text
Heart Rate
HRV
Sleep
Temperature
SpO2
Activity
```

### Output

```text
Mobile
  ↓
API
  ↓
Database
  ↓
ML pipeline
```

works end-to-end.

---

# PHASE 3 — PERSONAL BASELINE

### Weeks 5–6

Member 1 leads.

Build:

```text
Historical Data
      ↓
Cleaning
      ↓
Feature Engineering
      ↓
Personal Baseline
      ↓
Current Data
      ↓
Deviation Detection
```

### Output

The system understands the user's normal pattern.

---

# PHASE 4 — SENSOR INTELLIGENCE

### Weeks 7–8

Member 2 leads.

Build:

- Health Connect
- Sensor ingestion
- Data validation
- Signal quality
- Sensor fusion
- Camera prototype

### Output

Real health signals can enter the system.

---

# PHASE 5 — AI GUARDIAN

### Weeks 9–10

Member 3 leads.

Build:

- AI chat
- RAG
- Health explanations
- Structured insights
- Safety engine
- Alerts

### Output

The user can ask questions and receive explanations based on available health evidence.

---

# PHASE 6 — REAL DEVICE TESTING

### Weeks 11–12

Integrate:

- Android Health Connect
- Supported wearable
- Real data
- Optional BLE

Do not attempt every device.

Start with one reliable data source.

---

# PHASE 7 — FINAL INTEGRATION

### Weeks 13–14

All members work together.

Complete:

- UI
- Backend
- ML
- AI
- Alerts
- Security
- Testing
- Documentation
- Demo

---

# 🎯 MVP — FIRST VERSION

The first working version should contain:

## 1. User Profile

Basic information and permissions.

## 2. Health Data

At minimum, where available:

- Heart rate
- HRV
- Sleep
- Activity
- Temperature

## 3. Personal Baseline

Learn:

> "What is normal for this user?"

## 4. Anomaly Detection

Detect:

> "Today's pattern is different."

## 5. Multimodal Fusion

Combine multiple signals.

## 6. AI Explanation

Explain:

> "Why is today's health/recovery pattern different?"

## 7. Safety Engine

Possible actions:

- Observe
- Re-measure
- Give appropriate guidance
- Alert caregiver
- Escalate when appropriate

## 8. Health Timeline

Show changes over time.

---

# 🚫 FEATURES TO LEAVE FOR LATER

Do NOT make these mandatory for MVP:

- Custom wearable hardware
- Full retinal diagnosis
- Cancer diagnosis
- Kidney disease diagnosis
- Liver disease diagnosis
- Every smartwatch integration
- Every medical device
- OEM/OS-level integration

Build a strong core system first.

---

# 🔁 COMPLETE PRODUCT DATA FLOW

```text
             SMARTWATCH / PHONE
                     │
                     ▼
               HEALTH CONNECT
                     │
                     ▼
                ANDROID APP
                     │
                     ▼
                  FASTAPI
                     │
                     ▼
                PostgreSQL
                     │
                     ▼
          SIGNAL QUALITY ENGINE
                     │
                     ▼
          PERSONAL BASELINE ENGINE
                     │
                     ▼
             SENSOR FUSION
                     │
                     ▼
               SAFETY ENGINE
                     │
                     ▼
               AI GUARDIAN
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Dashboard   AI Chat     Alerts
```

---

# 👥 TEAM WORKING MODEL

We are building:

> **ONE APPLICATION**

not three separate projects.

Each member owns a module but contributes across the stack.

```text
                    ONE PROJECT
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       MEMBER 1       MEMBER 2       MEMBER 3
       Digital Twin   Sensors        AI Guardian
          │              │              │
          ├──── Mobile ──┼── Mobile ────┤
          ├──── Backend ─┼── Backend ───┤
          ├──── ML ──────┼── ML ────────┤
          └──────────────┼──────────────┘
                         ▼
                 ONE ANDROID APP
```

---

# 🗓️ DAILY TEAM WORKFLOW

Have a short daily discussion.

Each member answers:

### 1. What did I complete?

### 2. What am I doing today?

### 3. Am I blocked by anything?

Example:

```text
Member 1:
Yesterday → Health Profile API
Today     → Baseline service
Blocker   → Need final HealthEvent format

Member 2:
Yesterday → Health Connect
Today     → Sensor ingestion
Blocker   → None

Member 3:
Yesterday → Chat UI
Today     → AI API
Blocker   → Need baseline response format
```

Solve blockers quickly instead of letting one member wait for days.

---

# 🤝 TEAM RULE

Before coding major features, all three members should agree on:

```text
1. Architecture
2. Folder structure
3. Database schema
4. API contracts
5. Git branch strategy
6. Feature ownership
7. Coding conventions
8. Testing requirements
```

Once agreed, everyone follows this README.

If the architecture needs to change later, discuss it as a team and update this README.

---

# 🏁 FINAL TEAM PIPELINE

```text
                 SENSE
                   ↓
          Collect Health Data
                   ↓
              UNDERSTAND
                   ↓
        Personal Health Baseline
                   ↓
        Multimodal Sensor Fusion
                   ↓
              DETECT
                   ↓
        Meaningful Health Change
                   ↓
                GUARD
                   ↓
          Safety Engine + AI
                   ↓
        ┌──────────┼──────────┐
        ↓          ↓          ↓
     Explain    Recommend    Alert
```

---

# 👨‍💻 TEAM RESPONSIBILITY SUMMARY

| Area | Member 1 | Member 2 | Member 3 |
|---|---|---|---|
| Mobile | Profile/Dashboard/Timeline | Sensors/Health Connect | AI Chat/Alerts |
| Backend | Users/Baseline/Timeline | Sensors/Events | AI/Alerts/Safety |
| Database | Profile/Baseline | Sensor data | Insights/Alerts |
| ML | Personal baseline | Signal quality/Fusion | Safety |
| AI | Support | Support | RAG/LLM |
| Testing | Own module | Own module | Own module |
| Documentation | Own module | Own module | Own module |

---

# ⭐ PROJECT PRINCIPLE

The final system should demonstrate:

```text
SENSE
   ↓
UNDERSTAND
   ↓
PERSONALIZE
   ↓
DETECT
   ↓
EXPLAIN
   ↓
PROTECT
```

> **One repository. One mobile application. Three module owners. One integrated product.**

---

## 📚 SOURCE

The project's core concept is based on the provided **AI Personal Health Guardian** concept document, including its Personal Health Digital Twin, multimodal sensing, safety architecture, privacy principles and prototype roadmap..

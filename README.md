# 🚀 Buildathon: Make Wednesdays Great Again

**Masters' Union · For AI Developers · Winner gets Rs. 25,000**

> **Every team must build in a fork of this repository.** Projects not built in a fork of this repo won't be judged.

| | |
|---|---|
| **Date** | Wednesday, 18 November 2026 |
| **Hacking** | **3:00 PM – 7:00 PM IST** (code freeze at 7:00 PM sharp) |
| **Venue** | CDS Audi, 8th floor |
| **Prize** | Rs. 25,000 to the winning team |
| **Register your fork** | 👉 **[https://forms.gle/ZJUYKwTYjsMsVB2b9](https://forms.gle/ZJUYKwTYjsMsVB2b9)** (**deadline 3:30 PM IST**) |
| **Final submission** | Your fork as it stands at **7:00 PM IST**. There's nothing else to submit. |

> 🤖 **Using an AI coding agent?** Point it at [`AGENTS.md`](AGENTS.md). It has the full event brief, tracks, judging and rules in a form agents can read directly. Claude Code loads it automatically through `CLAUDE.md`, and Codex reads `AGENTS.md` natively.

---

## 🎯 Pick one build track

| # | Track | Brief |
|---|---|---|
| **01** | **Build for the Physical World** | Make a real-world task easier, faster or more reliable. Show it in a realistic scenario. |
| **02** | **Build for AI Agents** | Find something an agent struggles with. Build the tool that fixes it, then demo the agent using it. |
| **03** | **Build in Your Area of Expertise** | Pick a field you know firsthand. Ship a working product that improves how people handle it today. |

## ⚖️ How you'll be judged (each criterion is ⅓ of your score)

| Criterion | The question judges ask |
|---|---|
| **Working product** | Does it do what you say it does? Show the core workflow in your demo. |
| **Problem insight** | Who faces this problem, and why does it happen? |
| **Depth of execution** | How well did you solve the hardest part of the build? |

---

## Why fork this repo?

Everyone starts from the same commit (the **genesis commit**) at the same time. Organizers can then check that:
- all code was written **during** the Buildathon and not brought in from an earlier project,
- teams commit steadily instead of pasting in one huge AI-generated dump at the end,
- every repo stays public and visible while you build.

The organizers track every fork automatically: commits, timing and activity. Read [RULES.md](RULES.md) before you write any code.

---

## ✅ Setup (about 5 minutes, do it at 3:00 PM)

**In short:** fork → register your fork in the form **by 3:30 PM** → build → push before 7:00 PM.

### 1. Fork this repo
Click **Fork** (top right). On the fork screen:
- **Owner:** one team member's personal account. Only **one fork per team**.
- **Repository name:** `buildathon-<team-name>`, for example `buildathon-byte-bandits`
- Click **Create fork**.

> ⚠️ Don't download a ZIP or copy the files into a new repo. **It has to be a real GitHub fork**, or the tracker can't see you.

### 2. Keep it public
Forks of a public repo are public. **Don't make it private, archive it, or delete it** until judging is over.

### 3. Add your teammates
In your fork: **Settings → Collaborators → Add people**. Add each teammate's GitHub account so their commits count toward the team.

### 4. Enable Actions
Open the **Actions** tab of your fork and click **"I understand my workflows, go ahead and enable them"**. This runs the automatic check on every push.

### 5. Make your registration commit (your first commit)
Fill in [`team.json`](team.json). `track` must be one of `physical-world`, `ai-agents` or `area-of-expertise`. Then:

```bash
git clone https://github.com/<your-username>/buildathon-<team-name>.git
cd buildathon-<team-name>
# edit team.json
git add team.json
git commit -m "register: <team name>"
git push
```

The **Hackathon check** in the Actions tab should go green ✅. If it's red, open the run to see what's wrong in `team.json`.

### 6. Register your fork (deadline: 3:30 PM IST)
👉 **[https://forms.gle/ZJUYKwTYjsMsVB2b9](https://forms.gle/ZJUYKwTYjsMsVB2b9)**

It's a 4-question Google Form: team name, fork link, track, team members. It connects your repo to the organizers' live tracker.

- Fill it in **once per team**, right after forking, and **no later than 3:30 PM IST**. **Teams that don't register can't be tracked.**
- Paste your **fork's** URL (`https://github.com/<you>/buildathon-<team-name>`), not this starter repo's.
- Need to change something? Use the **"Edit your response"** link on the confirmation page. Don't fill it in twice.
- **Final submission is automatic.** Whatever is pushed to your fork at 7:00 PM IST is what gets judged.

---

## 🛠 While you build (3:00 – 7:00 PM)

- Put your code anywhere in the repo (`app/`, `src/`, `frontend/`, `backend/`…). There's no required layout.
- **Commit early, commit often**, at least every 30 minutes of real work, with messages that say what changed.
- **Push regularly.** Commits you never push don't exist to the tracker.
- AI coding tools (Claude Code, Codex, Cursor, Copilot…) are **allowed and encouraged**. Keep `AGENTS.md` and `CLAUDE.md` in the repo; they keep your agent within the rules.
- Before 7:00 PM, replace the "Your project" section below with your project's README.

## 🧊 Code freeze: 7:00 PM IST

At 7:00 PM the tracker takes a snapshot of every fork. **Commits pushed after code freeze are ignored.** Judges look at your last commit before 7:00 PM.

## ❌ Things that get you flagged

- Rewriting history (`git push --force`, rebasing away the genesis commit, squashing everything into one commit)
- Commits dated before 3:00 PM
- One or two giant commits containing most of the project
- A repo that isn't a fork of this one, or that's private or deleted

See [RULES.md](RULES.md) for the full list.

---

## Your project

# 💊 MediGuard: Prescription & Blister-Pack Discrepancy Verifier

- **Team:** MediGuard (Akshat Dhaundiyal)
- **Track:** Build for the Physical World (`physical-world`), with a Healthcare & Eldercare focus
- **Problem:** Elderly patients and their caregivers in India juggle 5+ medicines with look-alike brand names. Dolo, Crocin and Calpol are all paracetamol; Brufen plus Ecosprin is a bleeding risk. Prescriptions are abbreviated or handwritten, strips have tiny print, and doses get doubled by accident when a second brand of the same salt is taken. Pharmacists are not always at hand, and many homes have poor connectivity.
- **What we built:** Photograph the prescription and the medicine strips (or drag in images). MediGuard extracts the drugs and returns Green/Amber/Red cards, a Morning/Afternoon/Night schedule, and a read-aloud warning in English or Hindi.
- **The hardest part:** making it *safe*, not just smart. The model never judges safety. Vision/OCR extracts text, local Gemma 4 E2B (temperature 0, JSON-schema constrained) normalises it, and a deterministic rule engine (`safety_engine.py`) decides: `DUPLICATE_SALT`, `DOSAGE_MISMATCH`, `DRUG_INTERACTION`, `EXPIRED_BATCH`. It maps ~40 Indian brands to salts, tolerates OCR typos with fuzzy matching, and flags anything it cannot identify instead of guessing. Offline by default (RapidOCR on CPU, so no VRAM fight with Ollama). If `GEMINI_API_KEY` is set, Gemini Vision is used instead and the images are sent to Google; the page says which mode ran.
- **How to run it:**
```bash
uv sync                           # creates .venv from pyproject.toml + uv.lock (exact versions)
ollama pull gemma4:e2b            # offline mode only
uv run uvicorn app:app --host 127.0.0.1 --port 8000
uv run pytest                     # rule-engine and extraction tests
```
Works the same on Windows, macOS and Linux. Without `uv`: `python -m venv .venv`, activate it, `pip install -r requirements.txt` (exported from the lock file), then `python -m uvicorn app:app --host 127.0.0.1 --port 8000`.

Open http://127.0.0.1:8000. Optional: to enable Gemini, set `GEMINI_API_KEY` in the shell before starting (`.env` is not auto-loaded): PowerShell `$env:GEMINI_API_KEY="..."`, bash `export GEMINI_API_KEY=...`.
- **Demo:** click **Scenario 2** for the trap: Dolo 650 + Crocin 500 (hidden duplicate paracetamol, plus Crocin expired), Brufen + Ecosprin (bleeding interaction), and Dolo 650 on the strip vs 500 prescribed. Click **Scenario 1** for the safe match. Then upload `fixtures/rx_sample.png` and `fixtures/strips_mismatch.png` to run the real OCR + Gemma pipeline (about 1-2 minutes on a 6 GB GPU, mostly model load).

_MediGuard is a safety aid, not medical advice._

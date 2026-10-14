# Routine Tracker

A Linux desktop app (GTK4 + libadwaita) that follows a fixed daily timetable and acts as one place to log fitness, study and routine. It reminds you when each block starts and ends, shows where you are lacking, and gives study advice from a local Ollama model.

## Setup

No installs needed on a GNOME-style desktop: it uses system packages (PyGObject, GTK 4, libadwaita, libnotify, PyCairo, PyYAML). Python 3.12+. Charts are drawn with PyCairo into textures, so the `python3-gi-cairo` package is not needed.

Optional, for study recommendations: [Ollama](https://ollama.com) running locally with a model you pulled (`ollama pull <model>`). The app uses the largest installed model; set `ROUTINE_TRACKER_OLLAMA_MODEL` to choose one. Nothing leaves your machine. llama3.2:1b works but gives loose advice; llama3.2:3b is noticeably better and still answers in about 5-15 s on CPU.

## Set up your schedule

    cp schedule.example.yaml schedule.yaml    # then edit schedule.yaml with your own blocks and goals

`schedule.yaml` and `data/` (your logs) are gitignored, so your personal routine is never committed. Without a `schedule.yaml` the app falls back to the example template.

## Run

    python3 -m routine_tracker                 # open the window
    python3 -m routine_tracker --background    # reminders only, window opens on next launch

Closing the window hides it so reminders keep working. Quit with Ctrl+Q or the quit button in the header bar.

## Install the app icon (launcher + start at login)

    packaging/install.sh              # adds "Routine Tracker" to your app menu and starts it in the background at login
    packaging/install.sh --uninstall  # removes them (your data is kept)

It writes to `~/.local/share` and `~/.config/autostart`. Because the app is already running in the background, clicking the icon just raises the window, so it opens instantly.

## Using it

Five tabs, each with its own colour:

- **Today**: a "Now" card for the current block with Done / Partial / Skip, today's score and streak, a "Needs attention this week" strip, the daily check-in, and the timeline.
  - Done on a normal block saves in one click. Partial and Skip open a dialog (Skip needs a reason). Click a status again to edit it.
  - **Study** blocks also ask for a subject and what you achieved. **Claude** blocks ask what you asked Claude to do.
  - **Daily check-in**: weight, steps, sleep, water, calories (all optional), plus **+ Workout** (type, minutes, details).
- **Fitness / Study / Routine**: all share one layout. Week or month with arrows, a score ring with change vs the last period, **Where you're lacking** (worst first), a weekday chart, then section details.
  - Fitness: weight, steps, sleep, water, workouts against your goals.
  - Study: hours by subject, achievements, Claude requests, subjects you dropped, and **Get recommendations** (local Ollama; takes a minute on CPU).
  - Routine: streak, best and toughest day, calendar, and why you skipped.
- **Overview**: the whole period at a glance, a ring per section (tap to open), and the calendar heatmap.

Scoring: done = 100%, partial = 50%, skipped or unlogged = 0%. Only finished blocks count, every block weighs the same, free time is not scored, and scoring starts on your first logged day. Study and workout hours are time-weighted (a partial block counts half its minutes).

Accountability: notifications at block start, at block end if unlogged, 15 minutes later if still unlogged, and a day review at `review_at`. The streak counts consecutive days at 80% or more.

## Customising the timetable

Edit your `schedule.yaml` (copied from `schedule.example.yaml`; quote times, 24h). `goals` sets daily targets (steps, sleep, water, calories, goal weight) and `sections` says which block categories feed Fitness and Study (Routine always covers everything). Each block has `key`, `name`, `start`, `end`, `category`, and optionally `scored: false` and `detail`. Past scores are recomputed from the current file, so renaming a `key` detaches its old logs.

## Data

SQLite file at `data/tracker.db` inside this folder (gitignored, so your logs are never pushed). Back it up by copying that file. Override with `ROUTINE_TRACKER_DB`; override the timetable file with `ROUTINE_TRACKER_SCHEDULE`.

## Test

    python3 -m unittest discover -s . -t .

## Structure

    schedule.example.yaml      the public template timetable (copy to schedule.yaml, which is gitignored)
    packaging/                 app icon, launcher template, install.sh
    data/                      your logs (created on first run, gitignored)
    routine_tracker/
      config.py                file locations
      schedule.py              loads the timetable
      store.py                 SQLite block logs and remarks
      lifelog.py               metrics, workouts, achievements, Claude requests
      goals.py                 targets and section mapping
      stats.py                 scores, streaks, per-period reports, gaps
      fitness.py / study.py    section reports
      ollama_client.py         tiny local Ollama client
      recommend.py             builds the study-coach prompt
      reminders.py             which notifications are due (pure logic)
      ui/                      theme + style.css, charts, pages, dialogs
    tests/                     unit tests for the logic layers (run against the template)

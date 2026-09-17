# Mileage and time based maintenance Reminders

## Problem Statement

I own one or more Subaru vehicles and I forget when routine maintenance is due.
Oil changes, tire rotations and brake fluid flushes are each due after a certain
distance travelled or a certain amount of time, whichever arrives first, and the
only place that information currently lives is my memory and a glovebox booklet.
I already know the odometer is readable from my MySubaru account, but nothing
connects that number to "you are overdue for an oil change". I do not want a
maintenance app, an account, or a subscription — I want a message on my phone.

## Solution

A personal Telegram bot, running on my own machine, that reads each Vehicle's
odometer from Subaru's servers once a day and tells me when a Reminder is Due.

I create a Reminder by chatting with the bot: I give it a name, a Mileage
Interval, a Time Interval, or both, and optionally when the service was last
performed. From then on the bot measures from that Baseline and messages me the
first time either interval is passed. If I ignore it, it Nags me on a cadence I
chose, up to four times, and then falls silent. When I have actually done the
service I tell the bot, it records a Service Event, and both clocks restart from
that point.

Everything is stored in a local SQLite database. No data leaves the machine
except the Subaru API calls and the Telegram messages.

## User Stories

### Creating Reminders

1. As a vehicle owner, I want to create a Reminder by chatting with the bot one
   question at a time, so that I do not have to remember a command syntax on a
   phone keyboard.
2. As a vehicle owner, I want to give a Reminder a free-text name such as "Oil
   change", so that the message I receive uses the words I think in.
3. As a vehicle owner, I want to set a Mileage Interval in miles, so that a
   Reminder tracks how far I have actually driven.
4. As a vehicle owner, I want to set a Time Interval in calendar months, so that
   services with a shelf-life come due even when the car barely moves.
5. As a vehicle owner, I want to set both a Mileage Interval and a Time Interval
   on the same Reminder, so that it comes Due on whichever is reached first.
6. As a vehicle owner, I want to set only one of the two intervals, so that I am
   not forced to invent a number for a dimension that does not apply.
7. As a vehicle owner, I want to be stopped from creating a Reminder with
   neither interval, so that I cannot create something that will never fire.
8. As a vehicle owner, I want to tell the bot when the service was last actually
   performed, so that the first Reminder is measured from reality rather than
   from the day I happened to set the bot up.
9. As a vehicle owner, I want the last-service answer to default to the current
   odometer and right now, so that the common case is one tap.
10. As a vehicle owner, I want to set a Nag Interval in days while creating the
    Reminder, so that I control how insistent that particular service is.
11. As a vehicle owner, I want the bot to read the current odometer during
    creation, so that the Baseline is a real number rather than a guess.
12. As a vehicle owner, I want creation to fail with a clear message if the
    odometer cannot be read, so that I never end up with a Reminder anchored to
    nothing.
13. As a vehicle owner with more than one Vehicle, I want to be asked which
    Vehicle a Reminder belongs to, so that my wife's Forester does not inherit
    my Outback's oil changes.
14. As a vehicle owner with exactly one Vehicle, I want that question skipped,
    so that the flow is as short as it can be.
15. As a vehicle owner, I want to see a summary of everything I entered and
    confirm it before the Reminder is saved, so that a mistyped interval is
    caught immediately.
16. As a vehicle owner, I want to abandon a half-finished creation flow, so that
    a change of mind does not leave junk in the database.
17. As a vehicle owner, I want a half-finished creation flow to survive the bot
    process exiting, so that walking away mid-conversation does not lose my
    answers.
18. As a vehicle owner, I want an abandoned flow to expire on its own after
    about thirty minutes, so that a stale conversation does not hijack my next
    message.

### Being reminded

19. As a vehicle owner, I want a Telegram message the first time a Reminder
    becomes Due, so that I find out without having to check anything.
20. As a vehicle owner, I want the message to name the service, the Vehicle, and
    which interval triggered it, so that I know what to actually do.
21. As a vehicle owner, I want the message to include the current odometer and
    how far past the interval I am, so that I can judge urgency.
22. As a vehicle owner, I want to be Nagged on my chosen cadence while a
    Reminder stays Due, so that a service I keep putting off is not forgotten.
23. As a vehicle owner, I want Nagging to stop after four Nags, so that the bot
    does not become noise I learn to ignore.
24. As a vehicle owner, I want a Reminder that has gone silent after four Nags
    to stay silent until I record a Service Event, so that ignoring something
    deliberately is respected.
25. As a vehicle owner, I want to receive messages at any hour without a quiet
    window, so that the behaviour is simple and predictable.
26. As a vehicle owner, I want each Due episode to notify me once even if the
    bot runs several times that day, so that I am not told the same thing twice.
27. As a vehicle owner, I want a Reminder with both intervals to fire only once
    when both are passed, so that crossing the second threshold does not produce
    a duplicate message.

### Recording that a service was done

28. As a vehicle owner, I want to tell the bot I performed a service, so that
    the Reminder restarts from that point.
29. As a vehicle owner, I want to record a Service Event whether or not the
    Reminder was Due, so that servicing early is not a special case I have to
    work around.
30. As a vehicle owner, I want recording a Service Event to reset both the
    mileage and the time Baseline, so that a Reminder does not fire again
    immediately on the interval that did not trigger.
31. As a vehicle owner, I want to pick the Reminder from a numbered list, so
    that I do not have to type a name containing spaces.
32. As a vehicle owner, I want to pass the list number directly when I already
    know it, so that the common repeat case is one short command.
33. As a vehicle owner, I want to supply the date the service was performed, so
    that recording it a week late does not silently grant me an extra week.
34. As a vehicle owner, I want to supply the odometer the service was performed
    at, so that a shop visit at a known reading is recorded accurately.
35. As a vehicle owner, I want the bot to work out the half I did not supply, so
    that I only have to remember one of the two numbers.
36. As a vehicle owner, I want the bot to tell me the complete Baseline it
    recorded and have me confirm it, so that an inferred value is never applied
    behind my back.
37. As a vehicle owner, I want to be told when the bot had to fall back to an
    older reading than my date, so that I know the inference was approximate.
38. As a vehicle owner, I want recording a Service Event to clear the Nag count,
    so that the next Due episode gets its full four Nags.

### Managing Reminders

39. As a vehicle owner, I want to list all my Reminders, so that I can see what
    the bot is tracking.
40. As a vehicle owner, I want the list to show miles remaining and days
    remaining for each Reminder, so that I can plan a garage visit.
41. As a vehicle owner, I want the list to show which Reminders are currently
    Due, so that the outstanding work is obvious at a glance.
42. As a vehicle owner with several Vehicles, I want the list grouped by
    Vehicle, so that I can read it.
43. As a vehicle owner, I want to delete a Reminder, so that a service I no
    longer care about stops bothering me.
44. As a vehicle owner, I want to confirm before a delete takes effect, so that
    a mistap does not destroy history.

### Vehicles and odometer

45. As a vehicle owner, I want the bot to discover the Vehicles on my MySubaru
    account, so that I never have to type a seventeen character VIN.
46. As a vehicle owner, I want to give each Vehicle a short display name, so
    that messages say "Outback" rather than a VIN.
47. As a vehicle owner, I want the odometer read once a day automatically, so
    that Reminders stay current without me doing anything.
48. As a vehicle owner, I want the bot to never wake my car to get a reading, so
    that it cannot contribute to a flat battery.
49. As a vehicle owner, I want the moment the Vehicle itself reported the
    reading to be stored, so that I can tell a fresh number from a stale one.
50. As a vehicle owner, I want a small history of recent readings kept, so that
    a Service Event dated in the recent past can be matched to a real odometer
    value.
51. As a vehicle owner, I want readings that have not changed to be skipped, so
    that a parked car does not fill the database with identical rows.

### Failure and setup

52. As a vehicle owner, I want a single failed odometer read to be logged and
    otherwise ignored, so that a transient Subaru outage is not an event in my
    day.
53. As a vehicle owner, I want to be alerted after two consecutive failed reads,
    so that a genuinely broken integration cannot leave me silently untracked.
54. As a vehicle owner, I want time-based Reminders to keep being evaluated when
    the odometer cannot be read, so that a Subaru outage does not stop the
    calendar.
55. As a vehicle owner, I want to complete Subaru's two-factor device
    registration once, interactively, during setup, so that the daily run never
    needs my attention.
56. As a vehicle owner, I want the registered device identity kept in my local
    configuration, so that I am not asked to re-register every run.
57. As a vehicle owner, I want only my own Telegram account to be able to talk
    to the bot, so that nobody else can read or change my maintenance history.
58. As a vehicle owner, I want the bot to run unattended on a daily schedule, so
    that I never have to start it myself.
59. As a vehicle owner, I want a command I send between scheduled runs to be
    answered at the next run rather than lost, so that the bot is slow but never
    forgetful.

## Implementation Decisions

### Domain

- The vocabulary in `CONTEXT.md` is binding: Vehicle, Odometer Reading,
  Reminder, Mileage Interval, Time Interval, Baseline, Service Event, Due, Nag,
  Nag Interval. Code, log lines and user-facing messages use these words.
- A Reminder is recurring, not one-shot. Absolute mileage goals ("timing belt at
  105,000") are not a separate concept; they are expressible as an interval with
  a chosen Baseline.
- A Reminder must carry at least one of Mileage Interval or Time Interval.
  Creation is rejected otherwise.
- A Baseline is a single point — one odometer value and one moment. It is never
  split into two independently advancing clocks. A Service Event replaces the
  whole point.
- Mileage Interval is stored in miles as an integer. Time Interval is stored as
  a whole number of calendar months and applied with `dateutil.relativedelta`,
  which clamps a nonexistent target date to the last day of the target month.
  Month arithmetic is not hand-rolled.
- Nag Interval is measured in days only, never in miles. A Reminder that is Due
  on a car that is not being driven must still Nag.
- A Due episode allows the initial notification plus at most four Nags, then
  falls silent. The counter is cleared only by a Service Event. Crossing a
  further multiple of the Mileage Interval while already Due does not restart
  Nagging, because it is still the same outstanding service.

### Modules

- `schema.py` holds the SQLAlchemy declarative schema and nothing else,
  following the sibling `phone-bill-setup` project. There are no migrations and
  no Alembic. A schema change means the owner deletes the database file and
  re-creates it; the application must never contain migration logic.
- Tables: Vehicles (VIN, display name), Reminders (Vehicle, name, the two
  intervals, Nag Interval, Baseline odometer and moment, Nag count, the state
  needed to avoid duplicate notification), Odometer Readings (Vehicle, miles,
  vehicle-reported moment), Service Events (Reminder, odometer, moment), pending
  interactive flow state, and a key/value application state table.
- Columns are kept lean. No `updated_at`. Derived values such as miles remaining
  are computed, not stored.
- A Subaru access module wraps `subarulink` and is the only place that library
  is imported. It exposes vehicle discovery and a single "current reading for
  this VIN" operation returning miles plus the vehicle-reported timestamp, or
  nothing.
- A reminder evaluation module is pure with respect to the outside world: given
  Reminders, the latest readings and the current moment, it decides which
  Reminders are Due and which need Nagging. It sends nothing itself.
- A Telegram module owns command parsing, the interactive flows, and message
  formatting.
- A single run entry point composes these: read updates, advance any pending
  flows, fetch odometers, evaluate, send.

### Subaru integration

- `subarulink` is pinned and only `fetch()` is used. `update()` is never called
  under any circumstance, because it wakes the vehicle and the library documents
  a 12V battery drain risk.
- A failed or throttled `fetch()` is treated as no reading for that run. The run
  does not fall back to anything and does not retry aggressively.
- The odometer parses to an integer or to nothing (`BAD_ODOMETER` is `None`).
  The `None` case is handled explicitly everywhere a reading is consumed.
- The stored moment is the Vehicle's own reported timestamp, which is timezone
  aware at minute resolution — not the time of the API call.
- Units are miles throughout. The kilometre field the API also returns is not
  used.
- Device registration is a one-time interactive step run by the owner during
  setup. The device identity it establishes lives in local configuration; the
  library persists nothing itself. The daily run assumes registration is already
  complete and fails loudly if it is not.
- Credentials, device identity and the Telegram token live in the environment,
  not in the database and not in the repository.

### Scheduling and runtime

- Per ADR 0001, this is not a daemon. launchd starts the process once a day at
  12:00; it drains the Telegram queue, fetches odometers, evaluates Reminders,
  sends messages, and then stays alive for a thirty minute idle window that
  resets on each message from the owner, so an interactive flow can be completed
  in one sitting.
- Daily, rather than the originally considered three days, because the Telegram
  Bot API retains undelivered updates for at most twenty four hours. A longer
  gap would discard commands rather than delay them.
- Odometers are fetched on every run. No application-level logic exists to skip
  runs; the scheduler is the only thing that decides when work happens.
- Interactive flow state is persisted to the database after every step, so a
  flow survives the process exiting, and expires after about thirty minutes of
  inactivity.
- Only the configured owner's Telegram user id is accepted. Messages from anyone
  else are ignored.
- There are no quiet hours.
- Dates and times are handled in local context, matching the sibling project.

### Commands

- `/add` starts the interactive creation flow.
- `/list` shows all Reminders with remaining miles, remaining days and Due
  state, grouped by Vehicle when there is more than one.
- `/done` with no argument lists Reminders as a numbered choice, then asks for
  the date or odometer, then shows the complete Baseline for confirmation.
  `/done <n>` and `/done <n> <date-or-odometer>` are shortcuts into the same
  flow, and still end at the confirmation step.
- A single supplied argument is read as a date if it is date-shaped and as an
  odometer otherwise. A date alone takes the newest Odometer Reading at or
  before that date, falling back to the oldest reading held while saying so. An
  odometer alone takes the current moment.
- `/delete` selects from the same numbered list and confirms before removing.
- `/rename` gives a Vehicle the short display name messages use (story 46),
  asking which Vehicle only when there is more than one.
- There is no `/edit` and no `/snooze`. Editing is delete plus add. Snoozing is
  what the four-Nag limit already does.

### Toolchain

- Python is pinned to 3.14 via `uv python pin`, because the current `subarulink`
  requires it. Dependencies are added with `uv add`; `pyproject.toml` and
  `uv.lock` are never edited by hand.
- `loguru` for logging, `python-dotenv` for configuration, SQLAlchemy for the
  database, `python-telegram-bot` for Telegram, `python-dateutil` for month
  arithmetic.
- f-strings only.
- A setup script performs dependency sync, database initialisation, the one-time
  Subaru device registration, and launchd installation.
- The repository is intended to be public: no secrets, no real VINs, no real
  names in committed files. `.env-example` documents every variable.

## Testing Decisions

### What makes a good test here

A good test drives the system the way the owner does — a message arrives, a day
passes, an odometer changes — and asserts only on what the owner can observe:
the Telegram messages sent, and the state that survives to the next run. It
never reaches for an internal function to check that it was called, and never
asserts on log output. If a test would break when the modules are rearranged
without any change in behaviour, it is testing the wrong thing.

### The seam

There is exactly one seam: the run entry point. It is parameterised by three
collaborators, and tests supply fakes for all three:

- an odometer source, scripted per Vehicle per run, able to return a reading, no
  reading, or raise;
- a chat transport, which yields a scripted list of inbound updates and records
  every outbound message;
- a clock, so that months and Nag days can be advanced without waiting.

The database is real SQLite, created fresh per test. It is not faked, because
the persistence behaviour — flows surviving a process exit, Baselines outliving
a run — is part of what is being tested.

No module below the run entry point gets its own seam. The evaluation module is
pure and can be called directly in a few focused tests of the Due and Nag rules,
but that is a convenience, not a second injection point.

### What is covered

- Reminder creation across every branch: mileage only, time only, both, neither
  rejected, with and without a stated last service, single Vehicle and multiple
  Vehicles, confirmation accepted and declined.
- A creation flow interrupted by the process exiting and resumed on a later run.
- A creation flow expiring after its inactivity window.
- Due detection on the Mileage Interval, on the Time Interval, and on whichever
  comes first when both are set, including the case where the second threshold
  is crossed later and must not produce a second message.
- Calendar month arithmetic at a month-end Baseline, confirming the clamp.
- Nagging on cadence, silence after the fourth Nag, and the counter clearing on
  a Service Event.
- Service Events recorded when Due and when not Due; with a date only, with an
  odometer only, and with neither; the fallback to the oldest held reading and
  the message that admits it; both Baselines resetting together.
- Odometer readings appended only on change, and the history trimmed to the
  three most recent per Vehicle.
- A single failed fetch logged and otherwise ignored; two consecutive failures
  producing an alert; time-based Reminders still evaluating while the odometer
  is unavailable.
- Messages from a Telegram user other than the owner being ignored entirely.

### Prior art

None. The sibling `phone-bill-setup` project has no test suite, so this spec
establishes the pattern rather than following one. Tests run under `uv run
pytest`.

## Out of Scope

- Editing an existing Reminder. Delete and re-add.
- Snoozing or dismissing a Reminder as a distinct action.
- Absolute mileage goals as a first-class concept.
- Any Subaru command that contacts the vehicle: remote start, lock, unlock,
  locate, horn, lights, and above all `update()`.
- Non-Subaru vehicles, and manual odometer entry as a routine input path.
- Cost tracking, service history reporting, shop details, parts, or receipts.
- Group chats, multiple owners, or any sharing. One Telegram user, full stop.
- A web interface, an API, or any hosted component.
- Predicting when a threshold will be crossed from average daily mileage.
- Quiet hours and notification batching.
- Database migrations of any kind.
- Kilometre support and non-US MySubaru accounts.

## Further Notes

- ADR 0001 records why this is a scheduled burst rather than a daemon, and why
  the schedule is daily. If command latency becomes annoying in practice, the
  recorded remedy is a second, more frequent launchd entry that only drains the
  Telegram queue — not converting this into a long-running process.
- The three-reading history per Vehicle exists to serve date-only Service
  Events. It is deliberately small; if a use for deeper history appears, the
  trim limit is the only thing that needs to change.
- The `subarulink` API surface was verified against the published source rather
  than taken from memory. The odometer field is miles, the reading carries the
  Vehicle's own timestamp at minute resolution, and `fetch()` is throttled at
  three hundred seconds server-side, which is well inside a daily schedule.
- Whether a Vehicle with no active MySubaru subscription reports an odometer at
  all is not documented. If the first run returns nothing for a Vehicle, that is
  the likely cause.

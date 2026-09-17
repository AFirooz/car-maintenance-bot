# Scheduled bursts, not a long-running daemon

The bot needs to read each Vehicle's odometer periodically and also hold
interactive Telegram conversations (`/add`, `/done`). A `KeepAlive` daemon would
answer commands instantly, but this is a personal tool whose reminders move in
thousands of miles, so we kept the project's standing rule that the scheduler —
not the application — decides when work happens: launchd starts the process
every day at 12:00, it fetches odometers and evaluates Reminders, then stays
alive for a 30-minute idle window that resets on each message from the owner so
an interactive flow can finish.

Daily was chosen over a longer gap because the Telegram Bot API keeps
undelivered updates for at most 24 hours ("Incoming updates are stored on the
server until the bot receives them either way, but they will not be kept longer
than 24 hours"). At a 3-day interval, a command sent shortly after a run would
be silently discarded before the next one.

## Consequences

- A command is answered at the next 12:00 run, so worst-case latency is ~24
  hours. Nothing is lost.
- Odometers are fetched on every run rather than every third one. This is
  Subaru's server-side cache (`fetch()`, never `update()`), so it costs one HTTP
  request and never contacts the car — cheaper than adding application-level
  logic to skip two runs out of three.
- Half-finished interactive flows are persisted to the database and resumed on a
  later run, so they survive the process exiting mid-conversation.
- If command latency becomes annoying, the fix is a second, more frequent
  launchd entry that only drains the Telegram queue — not converting this to a
  daemon.

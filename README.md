# car-maintenance-bot

Personal Telegram bot that reads a Subaru's odometer from MySubaru and reminds
you when maintenance is due, on mileage or elapsed time, whichever comes first.

## What it does

- Reads each vehicle's odometer once a day from Subaru's server-side cache. It
  never wakes the car.
- Tells you when a reminder is due, then nags on your chosen cadence up to four
  times before falling silent.
- Restarts both the mileage and the time clock when you record that a service
  was actually performed.
- Stores everything in a local SQLite database.

See [CONTEXT.md](CONTEXT.md) for the vocabulary and
[docs/adr/](docs/adr/) for the decisions behind the design.

## Setup

1. Copy [`.env-example`](.env-example) to `.env` and fill values.
2. Run `./setup.sh`. It syncs dependencies, creates the database, walks you
   through Subaru's one-time two-factor registration, and installs the launchd
   agent.

## Commands

- `/add` - create a reminder, one question at a time
- `/list` - show reminders with miles and days remaining
- `/done` - record that a service was performed
- `/delete` - remove a reminder
- `/rename` - rename a vehicle
- `/cancel` - abandon whatever is in progress

`/done` and `/delete` accept the number shown by `/list`, and `/done` also takes
a date or an odometer: `/done 1 41800` or `/done 1 2026-08-02`.

## Schedule

launchd runs the bot daily at 12:00. It fetches odometers, sends anything due,
then stays available for 30 minutes so an interactive flow can be finished. A
command sent between runs is answered at the next one.

## If Subaru rejects the login

Subaru returns one generic error, `invalidAccount`, whether the email is wrong,
the password is wrong, or the account has no connected services. After three
rejected logins with the same credentials the bot stops trying, because Subaru
locks accounts after repeated failures. Editing `SUBARU_USERNAME` or
`SUBARU_PASSWORD` in `.env` clears the block automatically.

## Schema changes

There are no migrations. If the schema in `src/schema.py` changes, delete the
database file and run `uv run src/init_db.py` again.

## Tests

`uv run pytest`

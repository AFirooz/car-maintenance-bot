# Car Maintenance Bot

Tracks scheduled maintenance for one or more Subaru vehicles by reading each
vehicle's odometer from Subaru's servers and notifying the owner over Telegram
when a service is due — on either distance travelled or elapsed time,
whichever comes first.

## Language

**Vehicle**:
A single car, identified by its VIN, whose odometer this project can read.
_Avoid_: Car, auto

**Odometer Reading**:
A distance value in miles reported by a Vehicle, paired with the moment the
Vehicle itself reported it — not the moment it was retrieved.
_Avoid_: Mileage, odo

**Reminder**:
A named maintenance service the owner wants to be told about, carrying a
Mileage Interval, a Time Interval, or both. It belongs to exactly one Vehicle
and recurs indefinitely rather than completing once.
_Avoid_: Alert, task, job, maintenance item

**Mileage Interval**:
The distance in miles a Vehicle must travel past a Reminder's Baseline before
that Reminder is Due.
_Avoid_: Mileage goal, threshold, target

**Time Interval**:
The number of calendar months that must elapse past a Reminder's Baseline
before that Reminder is Due.
_Avoid_: Timer, deadline

**Baseline**:
The odometer value and moment a Reminder measures its next occurrence from.
Set from the most recent Service Event, or from the Reminder's creation if the
service has never been recorded.
_Avoid_: Anchor, start, last service, reference point

**Service Event**:
The owner's record that a Reminder's service was actually performed, carrying
the odometer value and moment it was performed at. It may be recorded whether
or not the Reminder was Due, and it becomes the Reminder's new Baseline.
_Avoid_: Completion, done, reset, acknowledgement

**Due**:
The state of a Reminder whose Mileage Interval or Time Interval has been
passed, and for which no Service Event has been recorded since.
_Avoid_: Triggered, fired, overdue, expired

**Nag**:
A repeat notification for a Reminder that is already Due and has had no
Service Event recorded against it. A Reminder is Nagged at most four times
before falling silent.
_Avoid_: Resend, escalation, snooze

**Nag Interval**:
The distance or time between one Nag and the next for a single Due Reminder,
set per Reminder when it is created.
_Avoid_: Nag cadence, repeat interval

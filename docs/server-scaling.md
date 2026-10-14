# Polling and concurrent-player capacity

Source audit, 2026-10-14. No 1,000-player load test has been run; the figures below
are estimates of request volume, not measured capacity. No server behavior was
changed during this audit.

## Current transport

The client sends authenticated POST `/api/poll` requests containing the last event
cursor and `wait_ms: 1000`. Each client normally has one poll outstanding. The
server returns immediately when queued events exist, otherwise waits for events
for up to one second. Responses contain up to 32 persisted events plus profile,
matchmaking, subscription and match metadata. The client advances its cursor and
immediately polls again. Commands/chat use separate requests.

This is short-duration long polling, rather than a fixed one-second delivery
interval. Relevant events wake waiting requests, so a message does not normally
need to wait for the one-second deadline. Network travel time, processing and lock
contention still apply. Failed requests use the existing six-second client limit.

At 1,000 idle connected clients, the intended cadence produces roughly 1,000
poll requests/second, excluding network overhead and other commands. During events,
responses can complete sooner and request frequency increases. This also means
roughly one outstanding HTTP request per player, handled with server threads.

## Confirmed bottlenecks

- `backend/server.py` uses `ThreadingHTTPServer`: waiting requests occupy threads.
  Python's documentation does not recommend `http.server` for production.
- `Service.poll_once` runs inside `Store.transaction`, which uses one shared
  SQLite connection and global `RLock` with `BEGIN IMMEDIATE`. It writes presence
  and queue heartbeats and performs tournament maintenance, matchmaking twice,
  match deadline checks and metadata queries. A timed-out idle poll calls it
  before and after waiting, so the baseline can approach 2,000 transactions/second
  at the estimated 1,000-poll/second cadence.
- Every successful transaction calls the global condition's `notify_all`, even
  for unrelated presence/heartbeat updates. Waiting clients wake, contend for the
  same lock, check their own events and usually sleep again. This creates needless
  wakeups beyond the HTTP request rate.
- One serialized Bun subprocess performs simulation. It is called while the
  service transaction still holds the global store lock; slow turns can block
  unrelated polling, chat and commands. The gameplay computation already runs
  outside Python, but only one turn can use this worker at once.
- Tournament/bracket code scans and decodes saved match JSON. Matchmaking searches
  queue pairs; ranking paths repeatedly construct global league lists. Cost grows
  with queue size and accumulated records, not just currently connected players.

The current implementation should be treated as a local/development server until
load testing proves otherwise. Increasing HTTP threads or worker counts alone
will not remove the shared locks, duplicate work or simulation bottleneck.

## Recommended changes before targeting 1,000 players

1. Make polling an event read/wait operation. Move tournament scheduling,
   matchmaking and deadline work into dedicated jobs. Throttle presence updates
   and notify only recipients whose events changed.
2. Use a production async HTTP server so idle polls do not require one thread
   each. Retain legacy-client-compatible polling, with a wait safely below the
   six-second client timeout. Longer waits reduce idle request volume but do not
   fix contention by themselves. Socket push can be considered separately after
   checking the Flash/AIR deployment constraints.
3. Submit turns to a bounded pool of simulation processes outside database
   transactions. Persist a turn claim/checkpoint, simulate, then commit only if
   the match/turn still owns that claim. Preserve idempotency and replay records.
4. Add indexed match/tournament queries, cache league/tournament summaries and
   reduce unchanged metadata. Evaluate PostgreSQL for multi-process deployment;
   replacing SQLite without changing lock scope is insufficient.
5. Run staged load tests at 100/500/1,000 clients, distinguishing idle players,
   active matches, spectators and chat. Measure p95/p99 event/command latency,
   CPU/RAM, thread count, database-lock time, simulation queue delay and timeouts.
   Include simultaneous round deadlines and global chat broadcasts. Use measured
   results to determine hardware and worker count.

Python remains a reasonable choice for this turn-based game's service layer.
Async I/O is suited to waiting network connections; the number of simultaneous
players alone does not establish a language bottleneck. Rewriting in another
language would retain the current architectural problems unless those change too.

Primary references:
[Python HTTP server documentation](https://docs.python.org/3/library/http.server.html)
and [Python asyncio documentation](https://docs.python.org/3.13/library/asyncio.html).

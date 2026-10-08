# Laravel Redis Queue Connector

How Laravel's `Illuminate\Queue\RedisQueue` stores jobs in Redis, and how
`app/connectors/adapters/stacks/laravel.py` reads them back.

> **Evidence labels**
>
> **Verified** means the behavior was observed directly on a live Laravel queue.
>
> **Source** means the behavior was established by reading Laravel's source.
>
> Examples use generic identifiers and contain no customer data.

---

## Contents

- [Key layout](#key-layout)
- [The client prefix](#the-client-prefix)
- [Job lifecycle](#job-lifecycle)
- [The `:notify` list](#the-notify-list)
- [Queue names with colons](#queue-names-with-colons)
- [Payload shape](#payload-shape)
- [Mapping onto the Argus schema](#mapping-onto-the-argus-schema)
- [Adapter behavior and Redis cost](#adapter-behavior-and-redis-cost)
- [Known limitations](#known-limitations)
- [Reproducing these findings](#reproducing-these-findings)

---

## Key layout

`RedisQueue` keeps a queue in up to four Redis keys, all rooted at:

```text
{prefix}queues:{name}
```

| Key | Type | Written by | Purpose |
| --- | --- | --- | --- |
| `{prefix}queues:{name}` | LIST | `push()` → `rpush` | Pending payloads, FIFO |
| `{prefix}queues:{name}:notify` | LIST | `push()` → `rpush` | Worker wake-up marker |
| `{prefix}queues:{name}:reserved` | ZSET | Pop script → `zadd` | In-flight jobs by reservation deadline |
| `{prefix}queues:{name}:delayed` | ZSET | `later()` → `zadd` | Scheduled jobs by availability time |

### What the data structures mean

The pending queue is a Redis **LIST**. It stores the actual serialized Laravel
job payloads in queue order.

The reserved and delayed queues are Redis **ZSETs** (sorted sets). Their scores
are timestamps:

- `:reserved` uses the reservation deadline.
- `:delayed` uses the time at which the job becomes available.

This difference matters to the adapter:

```text
pending  → LIST → LLEN / LRANGE
reserved → ZSET → ZCARD / ZRANGE
delayed  → ZSET → ZCARD / ZRANGE
```

**Verified:** the pending key is a LIST holding one member per pending job. For
example, seven pending jobs produce `LLEN = 7`.

**Source:** `:reserved` and `:delayed` are ZSETs, not LISTs. Calling `LLEN` on
either produces:

```text
WRONGTYPE Operation against a key holding the wrong kind of value
```

The adapter therefore uses `ZCARD` for counts and `ZRANGE` when it needs the
members.

Both ZSETs are created lazily. A queue that has never had a delayed or reserved
job may therefore expose only the pending and notify keys.

---

## The client prefix

Laravel's queue code works with:

```text
queues:{name}
```

The Redis client can add a configured prefix underneath that.

In `Illuminate\Redis\Connectors\PhpRedisConnector`, the Redis client receives
the configured prefix:

```php
$client->setOption(Redis::OPT_PREFIX, $config['prefix']);
```

The default prefix is:

```text
Str::slug(config('app.name')).'-database-'
```

For an application named `Argus`, one logical key can therefore have three
representations:

| Layer | Name |
| --- | --- |
| Laravel queue code | `queues:emails` |
| phpredis | prepends `argus-database-` |
| Redis stored key | `argus-database-queues:emails` |

This distinction matters when scanning Redis.

`SCAN` operates on the **stored Redis key**, so scanning for:

```text
queues:*
```

will not find anything when the connection has a prefix such as:

```text
argus-database-
```

Argus therefore stores the prefix per connection:

```yaml
connections:
  - name: argus-app
    redis_url: ${ARGUS_APP_REDIS_URL}
    stack: laravel
    prefix: argus-database-
```

An empty prefix is correct only for an application that does not configure a
Redis prefix. On a prefixed application, the wrong prefix can produce an empty
dashboard rather than an obvious error, so it should be configured deliberately.

---

## Job lifecycle

A Laravel Redis job can move through the following states.

### 1. Dispatch

**Source:** `push()` adds the serialized payload to the pending LIST with
`rpush`, then adds a wake-up marker to `:notify`.

```text
queues:{name}
    ↓
pending LIST
```

### 2. Delayed dispatch

**Source:** `later()` adds the payload directly to the delayed ZSET with `zadd`.

The ZSET score is the timestamp at which the job becomes available.

```text
queues:{name}:delayed
    ↓
wait for availability time
```

A delayed job does not move itself when its timestamp arrives. Laravel's worker
migration logic moves due jobs back to the pending LIST when a worker runs.

### 3. Pick-up

**Source:** a worker obtains a pending job and reserves it.

Conceptually:

```text
pending LIST
    ↓
reserved ZSET
```

The reservation is stored with a score of approximately:

```text
now + retry_after
```

The job's `attempts` value is incremented.

The reservation is a ZSET rather than a LIST because Laravel needs to find
reservations whose deadlines have expired.

### 4. Migration

**Source:** before processing another job, Laravel runs its migration logic.

It checks the delayed and reserved ZSETs for entries whose scores have passed.
Due entries are pushed back onto the pending LIST.

This produces two important recovery paths:

```text
delayed
   ↓ when due
pending
```

and:

```text
reserved
   ↓ reservation expires
pending
```

An expired reservation means Laravel can make the job available again after a
worker disappears or otherwise fails to complete it.

### 5. Success

**Source:** after successful processing, Laravel removes the job from the
reserved ZSET.

There is no normal Redis "completed jobs" queue.

```text
reserved
   ↓
removed
```

### 6. Failure

**Source:** when Laravel permanently fails a job, it removes the active Redis
representation and records the failure in the application's `failed_jobs` SQL
table.

Redis therefore does not provide the failed-job history used by Laravel's
`queue:failed` / `queue:retry` workflow.

---

## The `:notify` list

It is tempting to treat `:notify` as another copy of the queue. It is not.

**Verified:** its members are literal wake-up markers:

```text
$ redis-cli -n 2 lrange 'argus-database-queues:emails:notify' 0 1
1) "1"
2) "1"
```

The markers are not Laravel job payloads.

**Verified:** the key has no expiry:

```text
$ redis-cli -n 2 ttl 'argus-database-queues:emails:notify'
(integer) -1
```

The notify LIST is used to wake workers that are waiting for work. It should
therefore be treated as worker infrastructure, not as a second job store.

Its length can appear to track pushes closely enough to make it look like a
duplicate queue, but the contents are only wake-up markers.

Argus skips `:notify` entirely when building queue summaries and searching for
jobs.

---

## Queue names with colons

Queue names may themselves contain colons.

For example:

```text
reports:daily
```

produces keys such as:

```text
argus-database-queues:reports:daily
argus-database-queues:reports:daily:notify
```

The adapter must therefore **not** recover queue names by blindly splitting the
key on `:`.

Instead, it strips the known queue prefix and checks for at most one known
suffix:

```text
:reserved
:delayed
:notify
```

Everything before that suffix remains part of the queue name.

Conceptually:

```text
queues:reports:daily:reserved
       └────────────┘
       queue name
                    └────────
                      role
```

This preserves queue names containing colons.

There is an unavoidable ambiguity between a queue literally named:

```text
reports:notify
```

and the notify key belonging to:

```text
reports
```

Both can produce the same final key shape. Argus accepts that ambiguity.

---

## Payload shape

Each pending queue member is a JSON object.

**Verified** example shape, with identifying values replaced by placeholders:

```json
{
  "uuid": "00000000-0000-4000-8000-000000000000",
  "displayName": "App\\Jobs\\SendWelcomeEmail",
  "job": "Illuminate\\Queue\\CallQueuedHandler@call",
  "maxTries": 3,
  "maxExceptions": null,
  "failOnTimeout": false,
  "backoff": null,
  "timeout": null,
  "retryUntil": null,
  "data": {
    "commandName": "App\\Jobs\\SendWelcomeEmail",
    "command": "O:29:\"App\\Jobs\\SendWelcomeEmail\":1:{...}",
    "batchId": null
  },
  "createdAt": 1790000000,
  "id": "AbCdEfGhIjKlMnOpQrStUvWxYz012345",
  "attempts": 0,
  "delay": null
}
```

The outer payload is JSON. The `data.command` value is PHP-serialized job data
and is not currently decoded by the adapter.

| Field | Type | Read by Argus as |
| --- | --- | --- |
| `id` | string | `JobSummary.job_id` |
| `uuid` | string | fallback for `JobSummary.job_id` |
| `displayName` | string | Not exposed yet |
| `attempts` | int | `JobSummary.attempts` |
| `createdAt` | int | `JobSummary.pushed_at`, epoch seconds |
| `data.command` | string | Not decoded; PHP serialized |
| `maxTries`, `backoff`, `timeout`, `retryUntil`, `delay` | mixed | Not exposed yet |

`createdAt` is recorded as epoch seconds, not milliseconds.

---

## Mapping onto the Argus schema

| Argus field | Laravel source |
| --- | --- |
| `QueueSummary.pending` | `LLEN {prefix}queues:{name}` |
| `QueueSummary.reserved` | `ZCARD {prefix}queues:{name}:reserved` |
| `QueueSummary.delayed` | `ZCARD {prefix}queues:{name}:delayed` |
| `QueueSummary.failed` | Always `0` for the Redis-only adapter |
| `JobSummary.job_id` | Payload `id`, falling back to `uuid` |
| `JobSummary.attempts` | Payload `attempts` |
| `JobSummary.pushed_at` | Payload `createdAt` |
| `JobDetail.payload` | Decoded JSON payload |
| `JobDetail.payload_size_bytes` | Byte length of the raw Redis member |
| `JobDetail.complexity_score` | Always `0` |

### Adapter methods and Redis operations

| Adapter method | Redis operations |
| --- | --- |
| `list_queues()` | `SCAN`, then `LLEN` / `ZCARD` per queue key |
| `list_jobs()` | `LRANGE` on the pending LIST |
| `get_job()` | Queue-scoped `SCAN`, then `LRANGE` / `ZRANGE` until the ID matches |
| `list_failed_jobs()` | None; returns `[]` |
| `replay_job()` | None; raises `ReplayFailedError` |

---

## Adapter behavior and Redis cost

### `SCAN` is key discovery

The adapter uses:

```python
async for raw_key in redis.scan_iter(
    match=f"{self.prefix}{QUEUES}*",
    count=SCAN_COUNT,
):
    ...
```

`SCAN` incrementally walks Redis's keyspace instead of using `KEYS`.

`COUNT` is a **hint** to Redis about the amount of work per iteration; it is
not a guarantee that exactly that many keys will be returned.

The important property is that the adapter does not need to load the entire
matching keyspace into Python memory at once.

### `LRANGE` is a range operation

`LRANGE` reads members from a Redis LIST by index:

```text
LRANGE key start stop
```

For example:

```text
LRANGE queues:default 0 49
```

returns the first 50 members.

And:

```text
LRANGE queues:default 50 99
```

returns the next 50.

`LRANGE` itself is not pagination. The adapter's `offset` and `limit` parameters
use `LRANGE` to implement pagination.

For example:

```python
members = await redis.lrange(
    self._pending_key(queue),
    offset,
    offset + limit - 1,
)
```

This keeps `list_jobs()` from downloading the entire pending queue just to
render one page.

### `get_job()` is deliberately different

A job ID is an identifier inside the Laravel payload; Redis does not maintain an
index from that ID to the member's position.

Therefore, a read-only inspector cannot efficiently ask Redis:

```text
"Find the LIST member whose JSON id is X."
```

without maintaining a separate index.

The adapter therefore requires the queue name:

```python
get_job(job_id, queue)
```

This narrows the search from:

```text
all queues
    ↓
all queue members
```

to:

```text
one queue
    ↓
pending / reserved / delayed members
```

The queue name is therefore a meaningful optimization and should be supplied by
callers whenever it is known.

The adapter deliberately does **not** persist a LIST offset as a job's identity.
LIST positions are mutable: when jobs are popped, released, or added, other
jobs move to different indexes.

The stable lookup value is the Laravel job ID, not the Redis LIST position.

### Current limitation of `get_job()`

The current implementation still reads all members of each relevant structure
for the selected queue:

```python
await redis.lrange(raw_key, 0, -1)
```

or:

```python
await redis.zrange(raw_key, 0, -1)
```

That means a queue containing a very large number of jobs can make an individual
job lookup expensive.

This is an intentional trade-off for the current read-only adapter:

- no additional index is maintained;
- no Laravel queue state is modified;
- the lookup works across pending, reserved, and delayed jobs;
- the search space is at least narrowed to the caller-provided queue.

If large queues make this operation too expensive in practice, the next step
should be benchmarking and then considering a more targeted strategy rather than
prematurely introducing a second source of truth.

---

## Known limitations

### 1. Failed jobs cannot be seen from Redis

Laravel stores failed-job records in its SQL `failed_jobs` table.

Therefore:

```python
list_failed_jobs()
```

returns:

```python
[]
```

and:

```text
QueueSummary.failed = 0
```

This is a real capability gap, not an indication that there are definitely no
failed jobs.

Answering failed-job queries requires access to the application's database.

### 2. Replay is impossible from Redis alone

Laravel's failed-job replay workflow depends on the SQL failed-job record.

Therefore:

```python
replay_job()
```

raises `ReplayFailedError` instead of pretending that a Redis-only replay is
possible.

### 3. The job class is not exposed in `JobSummary`

Laravel includes `displayName` in the payload, but the current
`JobSummary` schema does not expose it.

A job list therefore currently shows the job ID rather than the Laravel job
class.

### 4. A growing `:reserved` count can indicate stale workers

Reserved jobs remain in the reserved ZSET until they are completed or their
reservations are migrated after expiry.

A growing reserved count can therefore be useful when investigating workers
that have disappeared or stopped processing jobs.

It should not, by itself, be treated as proof of a dead worker.

### 5. Redis values arrive as bytes

`RedisClient` uses:

```text
decode_responses=False
```

so keys and members arrive as `bytes`.

The adapter therefore explicitly decodes keys before parsing queue metadata and
passes raw member bytes to its JSON parser.

---

## Reproducing these findings

### Discover Laravel queue keys

Use `SCAN`, not `KEYS`:

```bash
redis-cli -n <db> --scan --pattern 'argus-database-queues:*'
```

`SCAN` incrementally discovers keys and is preferable for inspecting a
production Redis instance.

### Check the pending queue

```bash
redis-cli -n <db> type 'argus-database-queues:emails'
redis-cli -n <db> llen 'argus-database-queues:emails'
```

### Read one pending payload

```bash
redis-cli -n <db> lindex 'argus-database-queues:emails' 0
```

### Inspect the notify markers

```bash
redis-cli -n <db> lrange 'argus-database-queues:emails:notify' 0 1
redis-cli -n <db> ttl 'argus-database-queues:emails:notify'
```

### Confirm reserved and delayed types

Those keys are created lazily. If they do not exist on an idle queue, create
the relevant state first by dispatching a delayed job or observing a worker
processing a job.

Then run:

```bash
redis-cli -n <db> type 'argus-database-queues:emails:reserved'
redis-cli -n <db> type 'argus-database-queues:emails:delayed'
```

Both should report:

```text
zset
```

If either reports `list`, the adapter's Redis operation for that structure
needs to be revisited.

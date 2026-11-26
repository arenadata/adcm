# Notes

Commentary on non-obvious feature implementations: the kind of context that's useful while working with a feature,
but doesn't fit into [`ARCHITECTURE.md`](ARCHITECTURE.md) or [`CODESTYLE.md`](CODESTYLE.md) and isn't reliably found
if left only as comments scattered across the code.

To add a note, add a new section below with:
- Feature name as the heading
- Related tasks
- Authors/editors
- A short explanation of what's non-obvious about it and why it's implemented the way it is

Keep entries updated as the described behavior changes; stale notes are worse than no notes.

## Ansible environments per bundle contract

- Related tasks: ADCM-8521
- Authors/editors: Aleksandr Alferov

The image temporarily ships both musl and glibc builds of ansible `2.21`. The environments are not relocatable
(the build prefix is baked into the ELF interpreter, RPATHs and shebangs), so each one lives in `/venv` exactly where
its ansible image builds it:

- `/venv/2.16`: musl (there is no glibc build of `2.16`: contract `2.2` doesn't support it);
- `/venv/2.21`: glibc;
- `/venv/2.21-musl`: musl.

The `venv` value bundles declare is **not** changed: the directory is resolved at job run time by
`cm.legacy.utils.get_venv_dir_name` from the declared `venv` and the bundle's `contract_version`:

| `venv` | `contract_version`     | directory         |
|--------|------------------------|-------------------|
| `2.21` | `2.2` and newer        | `/venv/2.21`      |
| `2.21` | `1.0`, `2.0`, `2.1`    | `/venv/2.21-musl` |
| `2.16` | any (up to `2.1`)      | `/venv/2.16`      |
| `adcm` | any                    | `/venv/adcm`      |

Only `venv` values listed in `VENVS_WITH_MUSL_BUILD` (`2.21`) have a separate musl directory.

The same directory is used for `PATH` and `ANSIBLE_COLLECTIONS_PATH`, so the `arenadata.adcm` collection is copied
into each environment (see `Dockerfile`, `Dockerfile.redos`).

Once musl builds are dropped, remove `get_venv_dir_name` and the `2.21-musl` environment from the Dockerfiles.

## Сelery Task Monitoring

- Related tasks: ADCM-8495
- Authors/editors: Ikonnikova Polina

The scheduler passes adcm tasks in `QUEUED`, `RUNNING`, and `TERMINATING` that run through celery
to `CeleryTaskMonitor`. The monitor evaluates each task's liveness by examining its jobs.

### Settings

The scheduler process's environment variables configure intervals in seconds:

| Variable | Purpose |
|----------|---------|
| `SCHEDULER_JOB_MONITOR_POLL_INTERVAL` | Interval between monitoring checks |
| `SCHEDULER_JOB_INACTIVITY_THRESHOLD` | Trust gap: how long a job may continuously remain untracked with the same adcm status |

### One monitoring pass

`CeleryTaskMonitor.analyze_liveness` performs the following steps:

1. Retrieves information about Kombu messages and known celery tasks.
2. Loads the jobs of the adcm tasks being checked.
3. Updates monitoring data saved from the previous check.
4. Determines each task's liveness using the monitoring mode (`CeleryTaskMonitor.task_interruption_mode`) and trust gap.
5. Returns tasks grouped by `ALIVE`, `UNKNOWN`, and `DEAD`.

### Which jobs are considered

`CeleryTaskMonitor._get_analyzed_jobs` returns two sets of job ids: tracked jobs and problem jobs
(jobs whose execution could not be confirmed).

Jobs with a terminal status are skipped. The checked statuses are `CREATED`, `SCHEDULED`, `QUEUED`, `RUNNING`,
`REVOKING`, and `TERMINATING`. Finished jobs do not contribute to the task's liveness assessment.

A job is considered tracked if at least one of the following conditions holds:

- Its `worker_id` is set and appears among the ids returned by celery inspect.
- A Kombu message matches the job's adcm job id or its `worker_id`; matching by adcm job id also works
  before `worker_id` is set.

A `CREATED` job without a `worker_id` or confirmation from these sources may be waiting for preceding steps
in the execution plan, so its absence is not considered a problem.

### Two task interruption modes

`task_interruption_mode` selects how a task is assessed:

- `all_jobs_lost`: a task is classified as `DEAD` if no jobs are tracked and at least one of them remains untracked
  with an unchanged adcm status for at least the trust gap.
- `any_job_lost`: a task is classified as `DEAD` if at least one job remains untracked with an unchanged adcm status
  for at least the trust gap, even if other jobs are tracked.

The default is `all_jobs_lost`.

| Jobs in the current pass | `any_job_lost` | `all_jobs_lost` |
|--------------------------|----------------|-----------------|
| No problem jobs, including tasks with no jobs | `ALIVE` | `ALIVE` |
| Problem jobs and at least one tracked job | `UNKNOWN`, then `DEAD` if at least one problem job remains untracked with an unchanged adcm status for at least the trust gap | `ALIVE`; the task's saved timers are cleared |
| Problem jobs but no tracked jobs | `UNKNOWN`, then `DEAD` if at least one problem job remains untracked with an unchanged adcm status for at least the trust gap | The same rule: `UNKNOWN`, then `DEAD` |

In `any_job_lost` mode, a running parallel job does not hide the loss of another job.
In `all_jobs_lost` mode, at least one tracked unfinished job is enough for `ALIVE`,
even if a previously lost job's timer has already reached the trust gap.

### UNKNOWN and job timers

Unless the task is classified as `ALIVE`, the monitor stores a list of `UntrackedJob` entries
with `id`, `since`, and `status` for its current problem jobs in `unknown_state_tasks`.

- When a problem job is first observed, `since` is set to the current UTC time.
- On the next check, `since` is preserved only if the same job remains a problem with the same adcm status.
- If a problem job's status changes, its timer restarts, even if the previous timer has already expired.
- A new problem job receives its own timer and does not inherit another job's elapsed time.
- Jobs that become tracked or are no longer problem jobs are removed from the saved list.
- For `ALIVE`, the entire task entry is removed. In `all_jobs_lost` mode, this also happens when problem jobs remain
  but at least one job is tracked. If confirmation later disappears, the timers start again.

A task is classified as `DEAD` if at least one current problem job remains untracked with an unchanged adcm status
for at least the trust gap. If its status changes, `since` is updated before this check.
Until then, the task is `UNKNOWN`. Expired timer entries remain stored for `DEAD` tasks;
they are cleared when the task recovers or is absent from a subsequent pass.

`ALIVE`, `UNKNOWN`, and `DEAD` are monitoring classifications, not persisted adcm task execution statuses.
For a `DEAD` task, the scheduler calls `MarkTaskBroken`: it attempts to mark the task `BROKEN`,
its `CREATED` jobs `REVOKED`, and its other unfinished jobs `BROKEN`.
If the task's status has changed in the meantime, the transition may not happen. `MarkTaskBroken` updates the database
and releases the lock, but does not terminate the remaining executors.

### Example: two parallel jobs and a lost celery pool process

An adcm task starts with three jobs: `job1` and `job2` run in parallel, while `job3` waits for both to finish.

```yaml
scripts:
  - group: parallel
    name: parallel_waits
    scripts:
      - name: job1
        script_type: ansible
        script: ./job.yaml
      - name: job2
        ...
  - name: job3
    ...
```

The corresponding process tree inside the worker container is:

```text
celery main process — Pid 10 (shared by the worker)
├── celery pool process — Pid 11 (job1, id 20)
│   └── Ansible — Pid 13 (job1, id 20)
│       └── child Ansible — Pid 15 (job1, id 20)
└── celery pool process — Pid 12 (job2, id 21)
    └── Ansible — Pid 14 (job2, id 21)
        └── child Ansible — Pid 16 (job2, id 21)
```

The two pool processes come from `--concurrency 2`. Each job launches Ansible as a subprocess in the same container;
Ansible can create its own children. The job's stored Pid identifies its main Ansible process,
not its celery pool process.

| Job | celery task id | celery pool Pid | Ansible Pid | Child Ansible Pid | adcm status |
|-----|----------------|-----------------|-------------|-------------------|-------------|
| 20 | `7a28ec98-e82c-4e59-afea-cef5eff891f8` | 11 | 13 | 15 | `RUNNING` |
| 21 | `fe92b1c5-addf-4732-9080-8e839ee2f6a7` | 12 | 14 | 16 | `RUNNING` |
| 22 | None | None | None | None | `CREATED` |

Initially, celery inspect reports both running jobs in `active_ids`. The additional reserved id
`8cd149a4-97be-4a3f-a7ad-a2e8c250db5f` cannot be identified from its UUID alone: reserved tasks can include
celery service tasks that do not necessarily correspond to an adcm job.

Suppose pool process `11` is killed. It can no longer wait for Ansible or update job `20` in adcm,
so that job's stored status remains `RUNNING`. Its Ansible processes may continue after losing their parent.
Once celery detects the lost pool process, job `20`'s celery task id disappears from inspect;
job `21` can keep running in pool process `12`.
A replacement pool process does not restore the killed process's execution context.

For both modes, assume checks every 10 seconds, a 30-second trust gap, no Kombu messages for job 20,
and job 21 remaining tracked. Jobs 20 and 21 stay `RUNNING`; job 22 is `CREATED` without a `worker_id`
and is therefore not considered a problem. `t=0` is the first check that observes job 20 as untracked.

If a Kombu message still matches job 20, it is considered tracked in both modes,
and losing its process alone does not start a timer.

#### `any_job_lost` mode

Job 20 becomes a problem job, and the monitor starts its timer. Tracked job 21 does not affect this timer.
If job 20 remains untracked with an unchanged status for the trust gap, the task becomes `DEAD`.

| Check | Jobs represented in inspect | Job 20 timer | Result |
|-------|-----------------------------|--------------|--------|
| Before the process is killed | 20, 21 | None | `ALIVE` |
| t=0 | 21 | Started | `UNKNOWN` |
| t=10 s | 21 | 10 s elapsed | `UNKNOWN` |
| t=20 s | 21 | 20 s elapsed | `UNKNOWN` |
| t=30 s | 21 | Trust gap reached | `DEAD` |

After `DEAD` and a successful `MarkTaskBroken` call, the task becomes `BROKEN`,
jobs 20 and 21 become `BROKEN`, and job 22 becomes `REVOKED`.
The task leaves monitoring, although job 21 may still be executing.

#### `all_jobs_lost` mode

As long as job 21 is tracked, the task remains `ALIVE` despite the loss of job 20.
The monitor clears the task's saved timers, so job 20's time without confirmation does not accumulate.

| Check | Jobs represented in inspect | Saved timers | Result |
|-------|-----------------------------|--------------|--------|
| Before the process is killed | 20, 21 | None | `ALIVE` |
| t=0 | 21 | None | `ALIVE` |
| t=10 s | 21 | None | `ALIVE` |
| t=20 s | 21 | None | `ALIVE` |
| t=30 s | 21 | None | `ALIVE` |

Losing job 20 alone does not cause monitoring to mark the task `BROKEN`.

##### Losing the last tracked job

Continuing the `all_jobs_lost` example, job 21 also disappears from inspect at `t=40 s`.
There are no confirming Kombu messages, and jobs 20 and 21 remain `RUNNING`.
Both timers start on this check: job 20's time without confirmation before `t=40 s` is not counted.

| Check | Tracked jobs | Saved timers | Result |
|-------|--------------|--------------|--------|
| t=40 s | None | Jobs 20 and 21: `since = t=40 s` | `UNKNOWN` |
| t=50 s | None | 10 s elapsed | `UNKNOWN` |
| t=60 s | None | 20 s elapsed | `UNKNOWN` |
| t=70 s | None | 30 s elapsed | `DEAD` |

After `DEAD`, the scheduler attempts to mark the task `BROKEN`, just as in `any_job_lost` mode.
If at least one unfinished job becomes tracked again before the trust gap is reached,
the result becomes `ALIVE`, and the entire task's saved timers are removed.

#### When a user terminates a problem job

Consider both modes with a 30-second trust gap. Job 20 is `RUNNING`, but its execution cannot be confirmed
through inspect or Kombu. The next job, 21, is still `CREATED` without a `worker_id` and is not considered a problem.
The user requests termination of job 20 only, not the entire adcm task.

At `t=30 s`, job 20's timer would have caused `DEAD` if its status had remained `RUNNING`.
However, by this check the scheduler has already changed the job's status to `TERMINATING`:
the monitor restarts the timer and returns `UNKNOWN`. Job 20 still has no confirmation in inspect or Kombu.

Assume the termination signal is delivered and the executor handles job 20's termination.
When the process exits due to SIGTERM, the executor records `ABORTED`, and the execution plan continues with job 21.
At `t=40 s`, job 20 no longer contributes to the assessment, while job 21's execution is confirmed through inspect.

| Check | Job 20 status | Job 21 state | Job 20 timer | Task monitoring result |
|-------|---------------|--------------|--------------|------------------------|
| t=0 | `RUNNING` | `CREATED`, no `worker_id` | Started | `UNKNOWN` |
| t=10 s | `RUNNING` | `CREATED`, no `worker_id` | 10 s elapsed | `UNKNOWN` |
| t=20 s | `RUNNING` | `CREATED`, no `worker_id` | 20 s elapsed | `UNKNOWN` |
| t=30 s | `TERMINATING` | `CREATED`, no `worker_id` | Restarted because the status changed | `UNKNOWN`, although the previous timer reached the trust gap |
| t=40 s | `ABORTED` | `RUNNING`, tracked | Removed; job 20 has finished | `ALIVE` |

In this scenario, the task never becomes `DEAD` and is not marked `BROKEN` by monitoring.
The user terminates job 20, while the adcm task continues executing its subsequent jobs.

#### Handling a lost process without monitoring

Killing a pool process is only one way to show how a job can become untracked.
Without scheduler monitoring, celery itself detects the lost process and records its task's failure,
but this does not immediately update the adcm job's `RUNNING` status. In this example, the chord waits for terminal
celery results from all parallel branches, including jobs that continue running. Only then does `chord_unlock`
propagate the group error to adcm finalization. Finalization fails because the lost job is still `RUNNING`
in adcm, and its error handler marks the task and its unfinished jobs `BROKEN`.
Thus, without monitoring, the adcm status change in this example happens only after the other parallel jobs finish;
celery may detect the lost process earlier.

## Explicit locks

- Related tasks: ADCM-8345
- Authors/editors: Egor Araslanov

It was decided to have explicit database-based locks for operations performed within jobs: internal scripts and ansible plugins.

Aim is to prevent random write conflicts changing them to strictly sequential operations.
Note that API operations can still be performed in parallel to job ones and one another.

Current lock is on transaction level, unleashed with commit/rollback.
It's not a context manager for that reason exactly, which should a bit leakage between core and implementation, but it's considered ok.

Interface is defined in `core.locks`, implementation in `cm.impl` with postgres-dependant `pg_advisory_xact_lock` usage.
Since this lock requires 2 integers to specify namespace and some "lock id", we use following format `4TTCCC` to define namespace:
- `4` - constant meaning Arenadata/ADCM (4-A)
- `TT` - object type code as 2 decimal numbers:
   - `0X` - reserved for "management"-level entities
   - `10` - `ADCM`
   - `11` - `Provider`
   - `12` - `Host`
   - `13` - `Cluster`
   - `14` - `Service`
   - `15` - `Component`
- `CCC` - lock "aspect" code to allow multiple granual locks on given object (`000` - reserved for "whole object"), 
  other codes can be checked in implementation

Note that advisory locks doesn't mean any semantics in namespaces, format above is self-made,
just "some sense" is added to it, so may be reworked later if required.

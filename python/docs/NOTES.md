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

## Task's mapping delta: who writes it, who reads it, what is assumed

**Related tasks:** ADCM-8482 (cross-cluster bundle integration: `host_manage` / `host_group_manage` internal scripts)

`TaskLog.hostcomponentmap` stores a task's mapping delta (`core.action.types.TaskMappingDelta`). Three different
parties write or read it, and the code relies on assumptions that:

**Regular (non-wizard) actions.** An action declaring `hc_acl` launches through the mapping path: the submitted
mapping is checked at launch and stored as the task's delta (`use_cases/transition/job/schedule.py`). The inventory of
every job of the task takes the delta when one exists (`prepare_ansible_inventory`) - after ADCM-8482 the gate is
"the delta exists", which is equivalent to "the action declared `hc_acl`" only because declaring it always stores a
delta, possibly an empty one. `hc_apply` and the task finalizer commit the delta with `check_nothing`, so the
launch-time check is meant to be the single gate. A delta written after launch - the `host_manage` script's
`mapping_rules` - would reach the cluster unchecked, so the script checks the merged delta itself before storing it
(`check_host_component_mapping_change`, the same checks as the launch path).

**Wizard actions.** Wizard steps run as separate tasks with `task.action_process` set, and their mapping does not go
through the task's delta at all: the inventory uses the process's cumulative delta (`process_mapping_delta`), and
`hc_apply` reads the delta accumulated by the wizard steps. The task-level delta of a wizard step task stays `None`
(`set_post_init_task_attributes` is called without it in `use_cases/wizard.py`).

**Assumptions to recheck when `hc_acl` processing changes:**
- a task carries at most one mapping delta: the launch delta plus, possibly, additions a script of the same task made
  before `hc_apply` runs;
- nothing validates a delta at commit time - every writer must validate before storing;
- the wizard script schema (`DynamicWizardScript`) does not include `host_manage`, so a script-written task delta can
  only exist on a regular action; if wizard steps ever gain that ability, both delta readers (inventory preparation
  and `hc_apply`) have to learn to merge it with the process cumulative delta instead of ignoring it.

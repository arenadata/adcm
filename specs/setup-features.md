# Shared setup features

Serves CAP-3. Each scenario in `scenarios.md` cites the S-ids it needs. All of them live in one shared setup.

## Bundles

| Id | Feature | Why |
|---|---|---|
| S-B1 | Cluster bundle A v1: ≥3 services, ≥2 components each, actions on every level incl. **host actions** on cluster/service/component, config on every level, CHG allowed | cluster-hierarchy expansion |
| S-B2 | Cluster bundle B: **same action display names** as A on some levels, different services | shared business roles across bundles |
| S-B3 | Cluster bundle A v2 (upgrade target): one service removed, one added, one component removed, new and removed actions. Plain upgrade + upgrade with action using `bundle_switch` | upgrade re-apply, disappearing objects |
| S-B4 | Provider bundle P v1 + v2: host actions, provider/host config | provider hierarchy, provider upgrade |
| S-B5 | Bundle uploaded/deleted inside a scenario | E6, bundle-delete role cleanup |

## Topology

| Id | Feature |
|---|---|
| S-T1 | ≥2 clusters of bundle A (same role on different objects → leak detection), 1 cluster of bundle B |
| S-T2 | ≥2 providers, hosts in every state: free, in cluster unmapped, mapped to one component, mapped to several components across services |
| S-T3 | Host duplicates (original + duplicate) |
| S-T4 | CHGs on cluster, service, component, provider, with hosts and several config revisions |
| S-T5 | AHGs on cluster, service, component |
| S-T6 | Several ConfigLogs per object |

## Tasks and logs

| Id | Feature |
|---|---|
| S-J1 | Tasks on every target type (cluster, service, component, provider, host) |
| S-J2 | Host-action tasks (owner ≠ target) |
| S-J3 | AHG tasks |
| S-J4 | ADCM-owned task |
| S-J5 | Tasks with custom and check logs |
| S-J6 | Tasks launched before any qualifying policy existed vs after (TaskRole attached / unattached) |
| S-J7 | Rotated task: TaskLog deleted, TaskRole and GOPs left |

## RBAC

| Id | Feature |
|---|---|
| S-R1 | Users in 0/1/several groups; groups in 0/1/several policies |
| S-R2 | Policy per built-in business role kind: Cluster/Service/Provider Administrator, view/edit config roles, action business roles ("Cluster Action: X"), host-components/map roles |
| S-R3 | Non-parametrized policies (ModelRole-based: "ADCM User", "Create cluster", …) → model perms |
| S-R4 | Custom role combining several business roles |
| S-R5 | Same role in several policies on different objects (S-T1) |
| S-R6 | Overlapping policies: two policies grant the same GOP to the same group |
| S-R7 | Multi-object policy (2 services, 2 clusters, 2 hosts) |
| S-R8 | Multi-group policy |

## Groups

Prefix `G-`. These are not the scenario groups G1–G3.

| Group | Policies | Purpose |
|---|---|---|
| G-solo-* | exactly 1 each, one per role kind (S-R2/R3) | each role's output in isolation |
| G-overlap | 2+ policies granting the same rows (e.g. Cluster Administrator + Edit cluster configurations, same cluster) | S-R6 |
| G-cross | same role on cluster 1 and cluster 2 | S-R5, C3, C7 |
| G-multi-a, G-multi-b | both in one multi-group policy; G-multi-a also in another | S-R8, C2, G2.02 |
| G-launch-only | `view_owner` through one policy, `view_action` through another | C1 asymmetry |
| G-empty | in a policy, no users | writes don't depend on membership |
| G-idle | users, no policies | G2.07 target |

## Users

| User | Groups | Purpose |
|---|---|---|
| U-overlap | G-solo-(Cluster Administrator) + G-solo-(View cluster configurations), same cluster | removal keeps rows the other group still grants |
| U-mixed | G-solo-(Service Administrator) + G-solo-(Provider Administrator) + G-cross | removal drops a disjoint subset |
| U-multi | G-multi-a + G-overlap | overlap through multi-group and overlapping policies |
| U-launch | G-launch-only + a group with `view_action` | C1 per user |
| U-single | exactly one group | removal drops everything |
| U-none | no groups | add-to-group target |
| superuser | none | drives scenarios, absent from snapshots |

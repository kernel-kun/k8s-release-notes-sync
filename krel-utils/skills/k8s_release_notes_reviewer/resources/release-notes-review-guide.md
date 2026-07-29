# TL;DR

- Spell check & grammar (US English: "behavior", not "behaviour")
- Correct punctuation; period goes **outside** quotes — a "fork". not a "fork."
- Past tense, action verb first: Added / Fixed / Promoted / Graduated / Deprecated / Removed / Changed / Updated
- One note = one bullet, starts capitalized, ends with a period
- Backtick anything you'd type literally: flags (`--audit-log-maxsize`), field names/paths (`.spec.replicas`), commands (`kubectl get`), components (`kube-apiserver`, `kubelet`), metrics (`etcd_bookmark_total`), feature gates (`TopologyAwareWorkloadScheduling`), versions (`v1.36`, `v3.6.8`)
- **Never backtick an API kind** — write it verbatim in PascalCase: ConfigMap, Pod, ResourceClaim, EndpointSlice, PodGroup (not `ResourceClaim`)
- A kind and its field in one sentence: kind bare, field backticked — "the ResourceClaim `status.reservedFor` field"
- Graduation phases in Start case: Alpha, Beta, GA, Stable — never alpha/beta, never ALPHA/BETA
- Feature gates are PascalCase and backticked: `RelaxedServiceNameValidation`
- Field **values** stay plain — no quotes, no backticks: set `imagePullPolicy` to Always (not "Always", not `Always`); set `replicas` to 2 (not `2`)
- Release Note must be standalone — reader understands the change without opening the PR (verify the PR if a note is vague)
- Keep the PR/author/SIG trailer intact: `([#137609](url), [@enj](url)) [SIG API Machinery and Testing]`
- `ACTION REQUIRED:` prefix (uppercase) for any breaking change or migration step
- Put the note in the right Kind bucket (API Change / Feature / Bug or Regression / Deprecation / Other)
- No "we", "our", "just", "simply", "easily"; avoid "currently"/"new"/"now" as permanent claims (tie to a version instead)
- Avoid Latin: "for example" not "e.g.", "that is" not "i.e."
- Check links resolve; use real PR/issue numbers, not placeholders
- Merge true duplicates; keep separate cherry-picks (e.g. distinct Go patch bumps) separate
- Keep it concise and user-focused: what changed, what the user must do

# CheatSheet

A working reference for editing Kubernetes release notes, derived from the [Documentation Style Guide](https://github.com/kubernetes/website/blob/main/content/en/docs/contribute/style/style-guide.md) and adapted to how release notes actually read.

---

## 1. Voice, tense, and shape of a note

A note is a single bullet describing one change, from the user's point of view.

- **Past tense, action verb first.** Start with what happened: Added, Fixed, Promoted, Graduated, Deprecated, Removed, Renamed, Changed, Updated, Enabled, Disabled, Reverted.
  - This is the one place release notes **deliberately differ** from the style guide. The guide says "use present tense" for docs ("This command starts a proxy"). Notes describe a completed change in a shipped release, so past tense is correct and consistent across the file.
- **One change per bullet.** If a PR did two user-visible things, two sentences in the same bullet is fine; don't split one change across two bullets.
- **Capitalize the first word, end with a period.** Every bullet, including short ones.
- **Write for the cluster operator or developer**, not the contributor. Say what changed and what they must do, not how the code was refactored.

| Do                                                                          | Don't                                                                  |
| --------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `Promoted the ProcMountType feature to GA.`                                 | `This PR promotes ProcMountType to GA.` (present tense, meta)          |
| `Fixed kube-proxy log spam when all of a Service's endpoints were unready.` | `Fixes some log spam.` (vague, no component, no period)                |
| `Added the appProtocol field to kubectl describe service output.`           | `we added appProtocol to describe output` (lowercase, "we", no period) |

> **Real smell to catch:** line 293 of the v1.36 draft — "Fixed the total Pod resources computation." — is too vague to stand alone. A reader can't tell what was wrong or whether it affects them. Open the PR (#137683) and rewrite with the symptom, e.g. what was miscomputed and where it showed up (`kubectl describe`, a metric, etc.).

---

## 2. Backticks: the single biggest source of inconsistency

This is where most editing time goes. The rule has two halves and the second half is the one people miss.

### 2a. DO use backticks (inline code) for:

| Category                     | Example from v1.36                                                       |
| ---------------------------- | ------------------------------------------------------------------------ |
| Flags                        | `--concurrent-resourceclaim-syncs`, `--tls-curve-preferences`            |
| Object field names / paths   | `replicas`, `.spec.externalIPs`, `spec.stubPKCS10Request`                |
| Commands / subcommands       | `kubectl get`, `kubeadm config validate`                                 |
| Component & tool names       | `kube-apiserver`, `kube-controller-manager`, `kubelet`, `kube-scheduler` |
| Metric names                 | `etcd_bookmark_total`, `volume_operation_errors_total`                   |
| Feature gates                | `TopologyAwareWorkloadScheduling`, `RelaxedServiceNameValidation`        |
| Version strings              | `v1.36`, `v3.6.8`, `v1.26.2`                                             |
| Namespaces                   | `kube-system`                                                            |
| Config/struct/Go identifiers | `KubeletConfiguration`, `NewLifecycle`, `fake.NewClientset()`            |

### 2b. DON'T backtick API kinds — write them verbatim in PascalCase

The style guide is explicit: "API kinds such as StatefulSet or ConfigMap are written verbatim (no backticks); this allows using possessive apostrophes." Also in the guide: "A PersistentVolume represents durable storage…" is the **Do**; "`PersistentVolume`…" is the **Don't**.

| Do                                                                   | Don't                                                    |
| -------------------------------------------------------------------- | -------------------------------------------------------- |
| Added a deletion protection mechanism for PodGroup.                  | Added a deletion protection mechanism for `PodGroup`.    |
| The `kubelet` on each node acquires a Lease…                         | The `kubelet` on each node acquires a `Lease`…           |
| support for unknown references in ResourceClaim `status.reservedFor` | support for unknown references in `ResourceClaim` status |

(The component `kubelet` keeps its backticks; only the API kind Lease is bare.)

> **Real inconsistency in the v1.36 draft:** the same kind is backticked in some notes and bare in others — `ResourceClaim` / ResourceClaim, `EndpointSlice` / EndpointSlice, `PodGroup` / PodGroup. Pick the style-guide form (no backticks on the kind) and apply it consistently. Note that a **field** of the object _is_ backticked, so a single sentence often mixes both: "the ResourceClaim `status.reservedFor` field".

### 2c. Don't backtick plain values

For string/integer field values use normal style, no quotes, no backticks.

| Do                                      | Don't                                             |
| --------------------------------------- | ------------------------------------------------- |
| Set `imagePullPolicy` to Always.        | Set `imagePullPolicy` to "Always". / to `Always`. |
| Capped `nf_conntrack_max` to 1,048,576. | Capped `nf_conntrack_max` to `1048576`.           |

---

## 3. Capitalization rules that bite

- **Graduation phases use Start case: Alpha, Beta, GA, Stable.** The style guide Do/Don't: "Dynamic Resource Allocation (DRA) is Beta." not "…is beta."
  - The v1.36 draft is inconsistent here — it has both "Promoted … to Beta" (correct) and "Promoted the `watch_list_duration_seconds` metric from ALPHA to BETA" (wrong, all-caps). Normalize all-caps `ALPHA`/`BETA` to Alpha/Beta.
- **API kinds are PascalCase, never split into words:** PodTemplateList, not "Pod Template List"; EndpointSlice, not "Endpoint Slice".
- **Feature gates are PascalCase** and backticked: `WorkloadAwarePreemption`.
- **Sentence case for any heading** you add; the Kind headers (`### API Change`, `### Bug or Regression`) are fixed — don't rename them.
- **Proper nouns:** Kubernetes, Docker, Go, Prometheus, CoreDNS, Windows, Linux always capitalized.
- **etcd** is always lowercase. Write it plain when referring to the project (it's a proper noun, like Prometheus); backtick it only when naming the binary, process, path, or a metric (`etcd_bookmark_total`).

---

## 4. Punctuation & quotes

- **Period (and comma) go _outside_ the closing quote** — international standard, per the style guide: a "fork". not a "fork." This is the opposite of typical US convention, so double-check it.
- Use straight quotes; prefer rewording to avoid quoting at all (most quoted values should be unquoted normal style — see 2c).
- Serial/Oxford comma: follow the surrounding file (k8s notes generally use it).
- Don't end the SIG trailer with a period — it's metadata, not prose: `([#137609](url), [@enj](url)) [SIG API Machinery and Testing]`

---

## 5. The PR / author / SIG trailer

Every generated note ends with a fixed trailer. Preserve it exactly:

```
([#136399](https://github.com/kubernetes/kubernetes/pull/136399), [@tico88612](https://github.com/tico88612)) [SIG Apps, Instrumentation, Storage and Testing]
```

- Keep the PR link, the `@author` link, and the `[SIG …]` block.
- Don't reword or reorder the SIG list; it's generated from OWNERS/labels.
- If you split or merge notes, make sure each resulting note keeps a correct trailer — don't strand a note without its PR reference.

---

## 6. ACTION REQUIRED and the Urgent Upgrade Notes section

- Prefix any breaking change, rename, or required migration step with `ACTION REQUIRED:` (uppercase, colon). Example from the draft: "ACTION REQUIRED: Renamed metric `volume_operation_total_errors` to `volume_operation_errors_total`. If you are using custom monitoring dashboards … update them …"
- A good ACTION REQUIRED note states **what changed** _and_ **what the operator must do** before/after upgrade. Don't leave the action implicit.
- The most severe upgrade-blocking items belong under **Urgent Upgrade Notes**, not buried in API Change. When in doubt about placement, ask.

---

## 7. Grouping into the right "Changes by Kind" bucket

Put each note where readers expect it:

- **Deprecation** — something is now deprecated (still works, will go away).
- **API Change** — new/changed/removed API fields, kinds, validation, RBAC.
- **Feature** — new user-visible capability, flag, metric, kubectl output.
- **Documentation** — doc-only changes.
- **Failing Test / Bug or Regression** — fixes.
- **Other (Cleanup or Flake)** — refactors, log-level tweaks, dependency bumps, test flake fixes.

Common misfilings to fix: a pure metric promotion sitting under Feature when it's really instrumentation cleanup; a behavioral fix filed under Feature.

---

## 8. Word choices to avoid (straight from the guide)

| Avoid                                                   | Use                                                   |
| ------------------------------------------------------- | ----------------------------------------------------- |
| "we", "our", "us"                                       | name the component, or just the action ("Added…")     |
| "just", "simply", "easy", "easily"                      | drop the word; it adds nothing                        |
| "currently", "new", "now" (as a permanent claim)        | tie to the version: "In `v1.36`, …"                   |
| "e.g." / "i.e."                                         | "for example" / "that is"                             |
| jargon: "under the hood", "spin up", "turn up"          | "internally", "create", "start"                       |
| future promises ("will soon", "in an upcoming release") | only for announced deprecations with a target version |

Exception: "etc." is fine.

---

## 9. Deduplication & cherry-picks

- **Merge true duplicates.** The v1.36 draft has line 209 and 210 with identical text ("Updated node performance e2e tests to use PyTorch Wide-Deep workload instead of TensorFlow.") differing only by PR and SIG — collapse where they're genuinely the same change, or keep both with corrected, distinct descriptions if they touched different areas.
- **Keep distinct version bumps separate, but merge same-version pairs.** The v1.36 draft bumps Go several times across the cycle — `v1.25.6`, `v1.25.7`, `v1.26.0`, `v1.26.1`, `v1.26.2`. Different target versions are separate cherry-picks; don't collapse them. But the draft also has _same-version pairs_ that differ only by PR/author (two `v1.25.6` lines, #136257 and #136465; two `v1.25.7` lines, #136750 and #136982) — those are the genuine duplicates to merge. The same Go version even appears once under Feature and once under Other/Cleanup (`v1.26.2`, #138299 and #138261) — reconcile to one entry in the right bucket.
- A revert (line 200, "Reverted the addition of the `image_id` field…") that cancels an earlier note (line 146 added it) — consider whether both should ship, or whether the net effect is "no change" and both should be dropped. Ask if unsure.

---

## 10. Things the docs style guide says that DON'T apply to notes

So you don't waste time "fixing" non-issues:

- **Manual line-wrapping** of paragraphs (for per-line diffs/localization) is a docs-source rule. Release notes are generated one-line-per-bullet — don't hand-wrap them.
- **Hugo shortcodes** ({{< note >}}, glossary tooltips, {{< caution >}}) are for website pages, not the notes draft.
- **Present tense.** Notes use past tense (see §1) — this is an intentional inversion of the docs rule.
- **Sentence-case page titles vs. front matter** rules are about Hugo pages, not the notes file.
- **"Avoid statements about the future"** is relaxed for documented, announced deprecations that name a removal version (e.g. "planned to be removed in `v1.39`") — that's expected and allowed in notes.

---
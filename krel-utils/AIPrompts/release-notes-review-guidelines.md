# Kubernetes Release Notes Review Guidelines

## Objective
This document provides comprehensive guidelines for AI-assisted review of Kubernetes release notes to ensure they are clear, accurate, professional, and follow established Kubernetes documentation conventions.

**Note:** These guidelines are based on the [Kubernetes Documentation Style Guide](https://kubernetes.io/docs/contribute/style/style-guide/) and adapted specifically for release notes.

---

## 1. Writing Style & Tone

### 1.1 Use Simple and Direct Language
- **Use clear, direct language** - avoid unnecessary phrases like "please" or "in order to"
- **Start with action verbs** that describe what changed: "Added", "Fixed", "Updated", "Removed", "Promoted", "Enabled", "Improved", "Introduced", "Migrated", "Graduated", "Locked"
- **Be objective and factual** - state what changed without opinions or marketing language
- **Avoid conversational tone** - no "we", "now you can", "this allows you to"

### 1.2 Tense and Voice
- **Use past tense** for completed changes: "Fixed", "Added", "Updated", "Promoted"
- **Use active voice** where possible - makes sentences clearer and more direct
- **Exception:** Use passive voice if active voice leads to awkward construction

### 1.3 Sentence Structure
- **Keep sentences concise** - one main idea per sentence
- **Keep paragraphs under 6 sentences** when multiple sentences are needed
- **Avoid redundant phrases** like "this PR", "this change", "this feature"
- **Avoid words that assume understanding** - no "just", "simply", "easy", "easily"

### 1.4 Examples of Good vs. Bad

| Do | Don't |
|:---|:------|
| Fixed static pod status displaying Init:0/1 when unable to retrieve init container status from container runtime. | Fix static pod status is always Init:0/1 if unable to get init container status from container runtime. |
| Updated kube-dns to `v1.26.7`. | bump kube dns to v1.26.7 |
| Added support for Pods to reference the same `PersistentVolumeClaim` across multiple volumes. | This PR adds support for pods to reference the same PVC across multiple volumes. |
| Optimized kube-proxy conntrack cleanup logic, reducing the time complexity of deleting stale UDP entries. | We have optimized kube-proxy conntrack cleanup logic which simply reduces the time complexity. |

---

## 2. Formatting & Code Style

### 2.1 API Objects - Use UpperCamelCase (PascalCase)
- **Always use UpperCamelCase** for API objects: `Pod`, `Service`, `Deployment`, `StatefulSet`, `PersistentVolumeClaim`, `ConfigMap`, `Secret`
- **Do NOT use backticks** for API object names - they are written verbatim
- **This allows possessive apostrophes**: "a Pod's status", "the Deployment's replicas"

| Do | Don't |
|:---|:------|
| The HorizontalPodAutoscaler resource is responsible for... | The Horizontal pod autoscaler is responsible for... |
| A PodList object is a list of Pods. | A Pod List object is a list of pods. |
| Every ConfigMap object is part of a namespace. | Every configMap object is part of a namespace. |
| The kubelet on each node acquires a Lease... | The kubelet on each node acquires a `Lease`... |
| A PersistentVolume represents durable storage... | A `PersistentVolume` represents durable storage... |

### 2.2 Use Backticks for Code Elements
Use backticks (`` ` ``) for:
- **Commands and tools**: `kubectl`, `kubeadm`, `kube-apiserver`, `kubelet`
- **Flags and options**: `--flag-name`, `--client-ca-file`
- **File paths**: `/etc/kubernetes`, `/var/lib/kubelet/kubeadm-flags.env`
- **API fields**: `.status.conditions`, `.spec.resources`, `imagePullPolicy`
- **Namespaces**: `kube-system`, `default`
- **Version numbers**: `v1.35`, `v1.34.0`, `v3.6.5`
- **Feature gates**: `DynamicResourceAllocation`, `InPlacePodVerticalScaling`
- **Metric names**: `apiserver_request_sli_duration_seconds`
- **Environment variables**: `KUBECTL_KYAML`

| Do | Don't |
|:---|:------|
| The `kubectl run` command creates a Pod. | The "kubectl run" command creates a Pod. |
| Set the value of the `replicas` field in the configuration file. | Set the value of the "replicas" field in the configuration file. |
| Run the process as a DaemonSet in the `kube-system` namespace. | Run the process as a DaemonSet in the kube-system namespace. |
| The `kubelet` preserves node stability. | The kubelet preserves node stability. |
| Run the process with `kube-apiserver --client-ca-file=FILENAME`. | Run the process with kube-apiserver --client-ca-file=FILENAME. |

### 2.3 Starting Sentences with Component Names
When starting a sentence with a component name, include the article "the" before backticked names:

| Do | Don't |
|:---|:------|
| The `kubeadm` tool bootstraps and provisions machines in a cluster. | `kubeadm` tool bootstraps and provisions machines in a cluster. |
| The kube-scheduler is the default scheduler for Kubernetes. | kube-scheduler is the default scheduler for Kubernetes. |

### 2.4 Field Values - No Quotes or Backticks
For string and integer field values, use normal style without quotation marks or backticks:

| Do | Don't |
|:---|:------|
| Set the value of `imagePullPolicy` to Always. | Set the value of `imagePullPolicy` to "Always". |
| Set the value of `image` to nginx:1.16. | Set the value of `image` to `nginx:1.16`. |
| Set the value of the `replicas` field to 2. | Set the value of the `replicas` field to `2`. |

### 2.5 Punctuation
- **Always end with a period** - every release note should be a complete sentence
- **Use periods consistently** even for short notes
- **Use colons** to introduce lists or explanations
- **Punctuation outside quotes** - follow international standard: `events are recorded with an associated "stage".` (not `"stage."`)

### 2.6 Component Name Prefixes
- **Prefix component-specific notes** with the component name followed by a colon
- **Use lowercase for component prefixes**: `kube-apiserver:`, `kubelet:`, `kubeadm:`
- **Examples:**
  - `kube-apiserver: Fixed an issue where...`
  - `kubelet: Fixed reloading of server certificate files...`
  - `kubeadm: Fixed a bug where...`

---

## 3. Technical Accuracy

### 3.1 Component and Tool Names
**Exact names to use:**
- `kube-apiserver` (not apiserver, api-server, or API server)
- `kube-controller-manager` (not controller-manager)
- `kube-scheduler` (not scheduler)
- `kube-proxy` (not proxy)
- `kubelet` (not Kubelet)
- `kubectl` (not Kubectl)
- `kubeadm` (not Kubeadm)
- `etcd` (not Etcd or ETCD)
- CoreDNS (not coredns or core-dns)

**When to use descriptive names:**
Use general descriptors when appropriate for clarity:

| Do | Don't |
|:---|:------|
| The Kubernetes API server offers an OpenAPI spec. | The apiserver offers an OpenAPI spec. |
| Aggregated APIs are subordinate API servers. | Aggregated APIs are subordinate APIServers. |

### 3.2 Version References
- **Always use `v` prefix** for Kubernetes versions: `v1.35`, `v1.34.0`
- **Use `v` prefix** for dependency versions: `v3.6.5`, `v1.12.4`
- **Be specific** about version numbers when mentioning upgrades
- **Include version context** when relevant: "GA in `v1.34`", "beta in `v1.35`"
- **Use backticks** for version numbers

### 3.3 Feature Gates
- **Use exact UpperCamelCase names** with backticks: `DynamicResourceAllocation`, `InPlacePodVerticalScaling`
- **Specify state changes clearly**: "promoted to beta", "graduated to GA", "locked to enabled", "removed"
- **Include default state**: "enabled by default", "disabled by default"
- **Mention when gates are locked**: "locked to `true`", "locked to enabled"

### 3.4 API References
- **Use proper API notation**: `resource.k8s.io/v1`, `storage.k8s.io/v1beta1`
- **Reference fields with dot notation**: `.status.conditions`, `.spec.resources`
- **Use UpperCamelCase for API kinds**: `PodStatus.AllocatedResources`, `CustomResourceDefinition.spec.group`
- **Mention API groups** when relevant

### 3.5 Avoid Time-Sensitive Language
Avoid words that will quickly become outdated:

| Do | Don't |
|:---|:------|
| In version `v1.35`, ... | In the current version, ... |
| The Federation feature provides... | The new Federation feature provides... |
| Promoted to beta in `v1.35`. | Currently in beta. |

---

## 4. Content Structure

### 4.1 Bug Fixes
- **Start with "Fixed"** followed by the specific issue
- **Be specific** about what was broken and what now works
- **Include context** when helpful for understanding impact
- **Mention affected component** if not obvious

**Examples:**
- "Fixed a bug where `kubectl apply --dry-run=client` would only output server state instead of merged manifest values when the resource already exists."
- "Fixed a race condition in the CEL compiler that could occur when initializing composited policies concurrently."
- "kubelet: Fixed reloading of server certificate files when they are changed on disk and kubelet is dialed by IP address instead of DNS/hostname."

### 4.2 New Features
- **Start with "Added" or "Introduced"**
- **Describe what the feature does**, not just that it exists
- **Include alpha/beta/GA status** for new features
- **Mention feature gates** if applicable
- **Avoid "allows users to" or "enables users to"** - just state what it does

**Examples:**
- "Added support for Pods to reference the same `PersistentVolumeClaim` across multiple volumes."
- "Introduced the `--as-user-extra` persistent flag in `kubectl` for passing extra arguments during impersonation."
- "Added the `CloudControllerManagerWatchBasedRoutesReconciliation` feature gate."

### 4.3 Updates & Upgrades
- **Use "Updated" or "Upgraded"** for version bumps
- **Include version numbers** with `v` prefix in backticks
- **Be specific** about what changed

**Examples:**
- "Updated etcd to `v3.6.6`."
- "Upgraded CoreDNS to `v1.12.4`."
- "Updated cri-tools to `v1.35.0`."
- "Kubernetes is now built using Go `1.25.6`."

### 4.4 Deprecations & Removals
- **Use "Removed" or "Deprecated"** clearly
- **Explain impact** on users
- **Provide migration guidance** when relevant
- **Be specific** about what is deprecated/removed

**Examples:**
- "Removed the `--pod-infra-container-image` flag from `kubelet` command line."
- "Deprecated metrics will be hidden as per the metrics deprecation policy."
- "Marked `ipvs` mode in kube-proxy as deprecated, which will be removed in a future version of Kubernetes. Users are encouraged to migrate to `nftables`."
- "Dropped support for `policy/v1beta1` PodDisruptionBudget in `kubectl`."

### 4.5 Promotions (Alpha → Beta → GA)
- **Use "Promoted" or "Graduated"** for feature maturity changes
- **Specify the transition**: "to beta", "to GA", "to stable"
- **Mention feature gate changes**: "enabled by default", "locked to `true`"
- **Include previous state** when helpful: "from alpha to beta"

**Examples:**
- "Promoted the `EnvFiles` feature gate to beta and enabled it by default."
- "Graduated the fine-grained supplemental groups policy to GA."
- "Promoted `InPlacePodVerticalScaling` to GA."
- "Promoted the `MaxUnavailableStatefulSet` feature to beta and enabled it by default."

### 4.6 Performance Improvements
- **Use "Improved" or "Optimized"**
- **Quantify when possible**: "reduced time complexity", "89.8% coverage", "significantly improves performance"
- **Explain the benefit** to users

**Examples:**
- "Improved throughput in the `real-FIFO` queue used by `informers` and `controllers` by adding batch handling for processing watch events."
- "Optimized kube-proxy conntrack cleanup logic, reducing the time complexity of deleting stale UDP entries."
- "Improved HPA performance when using container-specific resource metrics by optimizing container lookup logic to exit early once the target container is found."

---

## 5. Special Cases

### 5.1 ACTION REQUIRED Notes
- **Use "ACTION REQUIRED:" prefix** in all caps at the start
- **Clearly state what users must do**
- **Explain consequences** of not taking action
- **Provide specific steps** when possible
- **Be direct and clear** about the requirement

**Example:**
```
ACTION REQUIRED: `failCgroupV1` will be set to true from `v1.35`. 
This means that nodes will not start on a cgroup v1 by default. This puts cgroup v1 into a deprecated state.
```

### 5.2 Multi-Component Changes
- **Group related changes** logically
- **Use bullet points** for multiple items (use `-` for unordered lists)
- **Maintain consistent formatting**
- **Indent with four spaces** for nested items

**Example:**
```
Enabled in-place resizing of pod-level resources.  
- Added `Resources` in `PodStatus` to capture resources set in the pod-level cgroup.  
- Added `AllocatedResources` in `PodStatus` to capture resources requested in the `PodSpec`.
```

### 5.3 Metrics
- **Include metric names** in backticks
- **Specify labels** when relevant: `{result}`, `{is_error}`, `{name=kube-controller-manager}`
- **Mention metric stage**: "alpha", "beta", "stable", "ALPHA", "BETA"
- **Use "metric" or "metrics"** explicitly for clarity

**Examples:**
- "Added ALPHA metric `scheduler_pod_scheduled_after_flush_total` to count pods scheduled after being flushed from unschedulablePods due to timeout."
- "Cloud Controller Manager now exports the counter metric `route_controller_route_sync_total`, which increments each time routes are synced with the cloud provider. This metric is in alpha stage."
- "metrics: Excluded `dryRun` requests from `apiserver_request_sli_duration_seconds`."

### 5.4 kubeadm-Specific Notes
- **Prefix with "kubeadm:"** (lowercase)
- **Be specific** about phases, subphases, and configuration
- **Mention configuration files** with full paths in backticks
- **Reference kubeadm commands** properly

**Examples:**
- "kubeadm: Fixed a bug where `ClusterConfiguration.APIServer.TimeoutForControlPlane` from `v1beta3` was not respected in newer kubeadm versions where `v1beta4` is the default."
- "kubeadm: Stopped applying the `--pod-infra-container-image` flag for the kubelet. During upgrade, kubeadm will attempt to remove the flag from the file `/var/lib/kubelet/kubeadm-flags.env`."

### 5.5 kubectl-Specific Notes
- **Use "Updated `kubectl <command>`"** format when describing command changes
- **Be specific** about what changed in the output or behavior
- **Use backticks** for the command name

**Examples:**
- "Updated `kubectl get` and `kubectl describe` human-readable output to no longer show counts for referenced tokens and secrets."
- "Updated `kubectl describe pods` to include the involved object's `fieldPath` (e.g., container name) in event messages."
- "Enabled `kubectl get -o kyaml` by default. To disable it, set `KUBECTL_KYAML=false`."

---

## 6. What to Avoid

### 6.1 Incomplete Information
- ❌ "NONE" - every PR should have a meaningful note or be excluded
- ❌ Vague descriptions: "Fixed a bug" (what bug? where?)
- ❌ Missing context: "Added flag" (which component? what does it do?)
- ❌ Ambiguous references: "it", "this", "the feature" (be specific)

### 6.2 Poor Grammar and Style
- ❌ Missing articles: "Add flag" → "Added the flag"
- ❌ Inconsistent tense: mixing past and present
- ❌ Run-on sentences without proper punctuation
- ❌ Missing periods at the end
- ❌ Starting sentences without articles: "`kubectl` handles..." → "The `kubectl` handles..."

### 6.3 Conversational Language
- ❌ Using "we": "We have updated..." → "Updated..."
- ❌ Using "you": "You can now..." → "Added support for..."
- ❌ Phrases like "please", "in order to", "allows users to"
- ❌ Words like "just", "simply", "easy", "easily"

### 6.4 Incorrect Formatting
- ❌ Missing backticks for technical terms
- ❌ Using backticks for API objects (use UpperCamelCase without backticks)
- ❌ Missing `v` prefix for versions
- ❌ Incorrect component names: "kube-dns" vs "CoreDNS"
- ❌ Quotes around field values: `"Always"` → `Always`

### 6.5 Time-Sensitive Language
- ❌ "currently", "new", "recent", "soon"
- ❌ "In the current version" → "In version `v1.35`"
- ❌ "The new feature" → "The feature" or just describe what it does

---

## 7. Review Checklist

When reviewing release notes, verify:

- [ ] **Starts with appropriate past-tense action verb** (Added, Fixed, Updated, Promoted, etc.)
- [ ] **Uses past tense consistently** throughout
- [ ] **Ends with a period**
- [ ] **Component names are correct** and formatted properly
- [ ] **Component-specific notes have prefix** (e.g., "kube-apiserver:", "kubelet:")
- [ ] **API objects use UpperCamelCase** without backticks (Pod, Service, Deployment)
- [ ] **Technical terms use backticks**: commands, flags, paths, fields, versions, feature gates
- [ ] **Version numbers include `v` prefix** and are in backticks
- [ ] **Field values have no quotes or backticks** (Always, not "Always" or `Always`)
- [ ] **Sentence is clear and concise** - no unnecessary words
- [ ] **Uses active voice** where possible
- [ ] **Avoids conversational language** - no "we", "you", "please", "simply"
- [ ] **Provides sufficient context** for users to understand impact
- [ ] **Grammar and spelling are correct**
- [ ] **No "NONE" entries** - either write a note or exclude
- [ ] **ACTION REQUIRED is clearly marked** when applicable
- [ ] **API references use correct notation** (`.status.conditions`, `resource.k8s.io/v1`)
- [ ] **Metric names are in backticks** with labels specified when relevant
- [ ] **Feature stage is mentioned** (alpha/beta/GA) for new features
- [ ] **No time-sensitive language** ("currently", "new", etc.)

---

## 8. Common Transformations

### 8.1 Capitalization and Formatting
```
Before: "bump kube dns to v1.26.7"
After:  "Updated kube-dns to `v1.26.7`."

Before: "add --concurrent-resourceclaim-syncs to configure kube-controller-manager resource claim reconcile concurrency"
After:  "Added the `--concurrent-resourceclaim-syncs` flag to configure kube-controller-manager resource claim reconcile concurrency."
```

### 8.2 API Object Formatting
```
Before: "Fixed a bug affecting `Pod` resources"
After:  "Fixed a bug affecting Pod resources"

Before: "The pod's status field was incorrect"
After:  "The Pod's status field was incorrect"
```

### 8.3 Adding Context and Component Prefix
```
Before: "Fixed volumeattachment cleanup"
After:  "Fixed volumeattachment cleanup in kube-controller-manager when CSI's attachRequired switches from true to false."

Before: "Fixed a bug where passing invalid DeleteOptions incorrectly returned a 500 status instead of 400."
After:  "kube-apiserver: Fixed an issue where passing invalid `DeleteOptions` incorrectly returned a 500 status instead of 400."
```

### 8.4 Removing Conversational Language
```
Before: "We have updated the component to use the new API"
After:  "Updated the component to use the new API."

Before: "You can now easily configure the timeout"
After:  "Added support for configuring the timeout."

Before: "This PR simply fixes a bug in the scheduler"
After:  "Fixed a bug in the scheduler."
```

### 8.5 Field Value Formatting
```
Before: "Set imagePullPolicy to `Always`"
After:  "Set `imagePullPolicy` to Always."

Before: "The value of replicas should be \"2\""
After:  "Set the value of the `replicas` field to 2."
```

### 8.6 Removing "NONE"
```
Before: "NONE"
Action: Either write a meaningful note or exclude the PR from release notes entirely.
```

---

## 9. Examples: Before & After

### Example 1: Version Update
**Before:** `bump kube dns to v1.26.7`  
**After:** `Updated kube-dns to `v1.26.7`.`

### Example 2: Feature Addition
**Before:** `add --concurrent-resourceclaim-syncs to configure kube-controller-manager resource claim reconcile concurrency`  
**After:** `Added the `--concurrent-resourceclaim-syncs` flag to configure kube-controller-manager resource claim reconcile concurrency.`

### Example 3: Bug Fix
**Before:** `Fix static pod status is always Init:0/1 if unable to get init container status from container runtime.`  
**After:** `Fixed static pod status displaying Init:0/1 when unable to retrieve init container status from container runtime.`

### Example 4: Feature Gate
**Before:** `locked the feature-gate VolumeAttributesClass to default (true) and bump VolumeAttributesClass preferred storage version to storage.k8s.io/v1`  
**After:** `Locked the `VolumeAttributesClass` feature gate to default (true) and updated the preferred storage version to `storage.k8s.io/v1`.`

### Example 5: kubectl Enhancement
**Before:** `kubectl get ingressclass now displays (default) marker for default IngressClass`  
**After:** `Updated `kubectl get ingressclass` to display a (default) marker for the default IngressClass.`

### Example 6: API Object Reference
**Before:** `Fixed a bug affecting `Pod` and `Service` resources`  
**After:** `Fixed a bug affecting Pod and Service resources.`

### Example 7: Component-Specific Fix
**Before:** `Fixed reloading of kubelet server certificate files`  
**After:** `kubelet: Fixed reloading of server certificate files when they are changed on disk and kubelet is dialed by IP address instead of DNS/hostname.`

---

## 10. Summary

**Key Principles:**
1. **Clarity** - Users should immediately understand what changed
2. **Consistency** - Follow Kubernetes documentation style conventions
3. **Completeness** - Include all relevant technical details
4. **Professionalism** - Maintain technical documentation standards
5. **Accuracy** - Ensure component names, versions, and technical details are correct
6. **Simplicity** - Use simple, direct language without jargon or assumptions

**Critical Formatting Rules:**
- API objects: UpperCamelCase, no backticks (Pod, Service, Deployment)
- Commands, flags, paths, fields, versions, feature gates: backticks
- Field values: no quotes or backticks (Always, not "Always")
- Component names: exact names with backticks (`kubectl`, `kube-apiserver`)
- Versions: `v` prefix in backticks (`v1.35`)
- Past tense, active voice, end with period

**Remember:** Release notes are technical documentation for users upgrading Kubernetes. They should be clear, accurate, and actionable without requiring users to read the PR or code changes. Follow the [Kubernetes Documentation Style Guide](https://kubernetes.io/docs/contribute/style/style-guide/) principles adapted for the concise format of release notes.

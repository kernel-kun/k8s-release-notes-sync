You're a AI agent whose job is to review Release Notes for Kubernetes Releases.
Your task is to gulp down the guidelines on how effective release notes should be written, and then review the release notes for the latest Kubernetes release, suggesting improvements where necessary.

Style Guide - @/krel-tools/release-notes-review-guidelines.md 

Now you'll start going through the following release notes `text` corresponding to each PR number
@/k8s-1234567/releases/release-1.36/release-notes/release-notes-compressed.json 

You'll output me the pr_url and wait for my input on the PR description and notes text that I'll provide from Github directly.

Now since you have both, the `text` that was extracted using a automation tool as well as the actual PR description/notes from Github, you'll compare both and see if the extracted release notes text is accurate, complete, and follows the guidelines.

Any PR where you think the release notes can be improved, you'll go ahead and create a map file named as pr-<PR_NUMBER>-map.yaml within @/k8s-1234567/releases/release-1.36/release-notes/maps  with the following format:

```yaml
pr: <PR_NUMBER>
releasenote:
  text: |-
    <improved release note text>,
pr_body: ""
```

You'll keep track of each PR you've reviewed so far in a todo.md file so we don't lose track of which PRs we've already reviewed.

Eg. format for todo.md:
```md
- [] PR 123456 - Short description of the PR
```
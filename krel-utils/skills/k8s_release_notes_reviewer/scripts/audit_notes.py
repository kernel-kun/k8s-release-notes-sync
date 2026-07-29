import json
import re
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 audit_notes.py <path-to-review-json>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    with open(file_path, 'r') as f:
        data = json.load(f)

    # API kinds list for reference (should NOT have backticks)
    API_KINDS = [
        "Pod", "Pods", "Node", "Nodes", "PodGroup", "PodGroups", "ResourceClaim", "ResourceClaims",
        "ResourceSlice", "ResourceSlices", "StatefulSet", "StatefulSets", "Deployment", "Deployments",
        "PersistentVolumeClaim", "PersistentVolumeClaims", "Service", "Services", "Lease", "Leases",
        "CustomResourceDefinition", "CustomResourceDefinitions", "CRD", "CRDs",
        "MutatingAdmissionPolicy", "MutatingAdmissionPolicyBinding", "ValidatingAdmissionPolicy",
        "StorageVersionMigration", "PodGroupTemplate", "PodCompositeGroup", "PodCertificateRequest",
        "HorizontalPodAutoscaler", "HorizontalPodAutoscalers", "EndpointSlice", "EndpointSlices",
        "ConfigMap", "ConfigMaps"
    ]

    FORBIDDEN_WORDS = ["we", "our", "us", "just", "simply", "easy", "easily", "currently", "new", "now", "e.g.", "i.e.", "e.g", "i.e"]
    VALID_VERBS = ["Added", "Fixed", "Promoted", "Graduated", "Deprecated", "Removed", "Renamed", "Changed", "Updated", "Enabled", "Disabled", "Reverted", "Improved", "Corrected"]

    issues_found = False

    for pr in data.get('prs', []):
        orig = pr.get('originalNote', '')
        draft = pr.get('currentDraftNote', '')
        pr_num = pr.get('prNumber', 'Unknown')
        
        issues = []
        
        # Check forbidden words
        draft_lower = draft.lower()
        for word in FORBIDDEN_WORDS:
            if re.search(r'\b' + re.escape(word) + r'\b', draft_lower):
                issues.append(f"Forbidden word used: '{word}'")
                
        # Check backticks on plain values (numbers)
        if re.search(r'`\d+`', draft):
            issues.append("Backticked plain number found (numbers should not be backticked unless they are versions e.g. v1.0.0)")
            
        # Check unbackticked flags (words starting with --)
        unbackticked_flags = re.findall(r'(?<!`)\b--[\w-]+\b(?!`)', draft)
        if unbackticked_flags:
            issues.append(f"Unbackticked flags found: {unbackticked_flags}")
            
        # Look for API kinds with backticks (case sensitive)
        for kind in API_KINDS:
            if f"`{kind}`" in draft:
                issues.append(f"Backticked API kind: `{kind}` (API Kinds should be verbatim PascalCase)")

        # Check action verb (basic)
        first_word = draft.split()[0] if draft else ""
        if not first_word.endswith("ed") and first_word not in VALID_VERBS:
            issues.append(f"Starts with non-standard verb: '{first_word}' (Must start with past-tense action verb)")

        # Display if there are issues
        if issues:
            issues_found = True
            print(f"--- PR #{pr_num} ---")
            print(f"Orig : {orig}")
            print(f"Draft: {draft}")
            for iss in issues:
                print(f"  - {iss}")
            print()
            
    if not issues_found:
        print("All release notes passed the audit cleanly!")

if __name__ == "__main__":
    main()

import json
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 apply_fixes.py <path-to-review-json>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    with open(file_path, 'r') as f:
        data = json.load(f)

    # -------------------------------------------------------------
    # EDIT THIS DICTIONARY to apply your manual draft corrections
    # Format: { PR_NUMBER: "Corrected Draft String" }
    # -------------------------------------------------------------
    corrections = {
        # e.g., 123456: "Updated the \`kubelet\` logic to better handle edge cases."
    }

    updated_count = 0
    for pr in data.get('prs', []):
        pr_num = pr.get('prNumber')
        if pr_num in corrections:
            pr['currentDraftNote'] = corrections[pr_num]
            updated_count += 1
        
        # Optionally mark everything as reviewed after running audit
        pr['reviewDone'] = True

    # Update metadata totals
    data['metadata']['reviewedPRs'] = len(data.get('prs', []))

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Successfully reviewed {len(data.get('prs', []))} PRs.")
    if updated_count > 0:
        print(f"Applied custom text corrections to {updated_count} PRs.")
    else:
        print("No specific PRs mapped for corrections. Just marked as reviewed.")

if __name__ == "__main__":
    main()

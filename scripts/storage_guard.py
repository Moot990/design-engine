"""Stop before generating more artifacts if repository storage is near its budget."""
import os
from engine.common import EngineError, request, response_json


def main():
    total = 0
    headers = {"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"], "Accept": "application/vnd.github+json"}
    for page in range(1, 11):
        value = response_json(request("GET", f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/actions/artifacts", service="Artifact storage check", retry_safe=True, headers=headers, params={"per_page": 100, "page": page}), "Artifact storage check")
        artifacts = value["artifacts"]
        total += sum(a["size_in_bytes"] for a in artifacts if not a["expired"])
        if len(artifacts) < 100:
            break
    else:
        raise EngineError("Too many artifacts to verify storage safely; archive/delete old engine artifacts first")
    print(f"Active repository artifacts: {total / 1_000_000:.1f} MB; generation cutoff: 350 MB")
    if total > 350_000_000:
        raise EngineError("Artifact budget reached; download and remove old artifacts before generating more")


if __name__ == "__main__":
    try:
        main()
    except EngineError as error:
        print("BLOCKED: " + str(error))
        raise SystemExit(2)

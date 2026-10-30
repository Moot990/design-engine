from __future__ import annotations

import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from .common import ROOT, read_csv


def weekly(state_dir, destination, today):
    today = date.fromisoformat(str(today))
    since = today - timedelta(days=6)
    rows = [r for r in read_csv(Path(state_dir) / "ideas.csv") if since.isoformat() <= r["date"] <= today.isoformat()]
    history = json.loads((Path(state_dir) / "history.json").read_text(encoding="utf-8"))
    publications = {k: v for k, v in history["publications"].items() if since.isoformat() <= v.get("date", "") <= today.isoformat()}
    statuses = Counter(v["status"] for v in publications.values())
    lines = [f"# Weekly report: {since} to {today}", "", f"- Ideas reserved: {len(rows)}", f"- Accepted image ideas: {sum(r['status'] == 'accepted' for r in rows)}", f"- Confirmed uploads: {statuses.get('published', 0)}", f"- Requests needing manual reconciliation: {statuses.get('inflight', 0) + statuses.get('unknown', 0)}", "", "## Platform results", "", "| Item | Platform | State | Remote ID |", "|---|---|---|---|"]
    for key, value in publications.items():
        lines.append(f"| {key} | {value['platform']} | {value['status']} | {value.get('remote_id', '')} |")
    lines.extend(["", "## Errors and generation outcomes", ""])
    for day, run in history["runs"].items():
        if since.isoformat() <= day <= today.isoformat():
            lines.append(f"- {day}: {run.get('status', 'unknown')}; " + "; ".join(run.get("warnings", [])))
    lines.extend(["", "## Metrics you enter", "", "Edit data/metrics.csv on GitHub. Never paste account credentials into metrics.", "", "| Platform | Views | Saves | Link clicks | Earnings SAR |", "|---|---:|---:|---:|---:|"])
    metrics = read_csv(ROOT / "data/metrics.csv")
    for platform in ("pinterest", "youtube", "digital-products"):
        relevant = [r for r in metrics if r["platform"] == platform and since.isoformat() <= r["week_start"] <= today.isoformat()]
        totals = []
        for field in ("views", "saves", "link_clicks", "earnings_sar"):
            try:
                totals.append(str(round(sum(float(r[field] or 0) for r in relevant), 2)))
            except ValueError:
                totals.append("check metrics CSV")
        lines.append(f"| {platform} | " + " | ".join(totals) + " |")
    lines.extend(["", "Review one strong and one weak post; note the room, style and teaching point.", "Check for distorted objects, misleading product matches and repetitive content.", "Downloads expire: archive wanted media and monthly packs before artifact retention ends.", "", "## Your notes", "", "Keep:", "", "Change:", "", "Stop:", ""])
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def day90(destination):
    Path(destination).write_text("""# Day-90 review

Start date: ____  Review date: ____  Total spend: 0 SAR

Use the last 28 days and the prior 28 days. These are working decision rules,
not promised performance benchmarks. Mark missing metrics as unknown, not zero.

| Platform | Views | Saves | Link clicks | Earnings SAR | Keep / change / cut | Evidence |
|---|---:|---:|---:|---:|---|---|
| Pinterest | | | | | | |
| YouTube Shorts | | N/A | | | | |
| Digital products | | N/A | | | | |

- Pinterest: compare saves/views and outbound clicks/views by style and room.
  Keep concepts with repeatable saves and outbound clicks. Change poor hooks or
  mismatched destinations. Pause weak variants after at least 10 distinct posts
  and 1,000 combined impressions; if exposure is lower, record insufficient data.
- Shorts: compare views, viewed-vs-swiped, retention and traffic to your channel
  profile. Description URLs are not clickable. Keep useful lessons with improving
  retention. Change weak openings or pacing. Cut a format after 10 distinct Shorts
  with persistently weaker retention than your own channel median.
- Products: compare store visits, sales, conversion and earnings, not pack count.
  Keep a theme with demand. Revise its preview and description after 100 qualified
  visits and no sales. Pause a theme with no evidence of demand after two revisions.
- Affiliate: calculate earnings per outbound click where attribution is available.
  Check the Egypt account's current attribution windows and exclusions. Never
  infer YouTube affiliate sales from video views alone.
- Overall: retain the channel combination producing qualified traffic or sales
  within the one-hour weekly budget. Do not buy traffic or add subscriptions.

One change to test for the next 30 days: ____
One format to stop: ____
Policy/account issues to fix: ____
""", encoding="utf-8")

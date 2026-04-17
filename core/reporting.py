from __future__ import annotations


def render_markdown(report: dict) -> str:
    conflict_count = report["summary"].get("conflict_count", len(report.get("conflicts", [])))
    requested_policy_pack = report["profile"].get(
        "requested_policy_pack",
        report["profile"].get("policy_pack", "generic-agentic"),
    )
    resolved_policy_pack = report["profile"].get("policy_pack", "generic-agentic")
    policy_resolution = report["profile"].get(
        "policy_resolution",
        report["summary"].get("policy_resolution", "default"),
    )
    lines = [
        "# Skill Auditor Report",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Generated at: `{report['generated_at']}`",
        f"- Skills audited: `{report['summary']['skill_count']}`",
        f"- Findings: `{report['summary']['finding_count']}`",
        f"- Requested policy pack: `{requested_policy_pack}`",
        f"- Policy pack: `{resolved_policy_pack}`",
        f"- Policy resolution: `{policy_resolution}`",
        f"- Rules version: `{report['summary'].get('rules_version', 'generic-agentic@1.0')}`",
        f"- Prompt version: `{report['summary'].get('prompt_version', 'generic-agentic@1.0')}`",
        f"- LLM provider: `{report['summary'].get('llm_provider', 'none')}`",
        f"- LLM findings: `{report['summary'].get('llm_finding_count', 0)}`",
        f"- LLM conflicts: `{report['summary'].get('llm_conflict_count', 0)}`",
        f"- Conflicts: `{conflict_count}`",
        f"- Highest conflict priority: `{report['summary'].get('highest_conflict_priority', 0)}`",
        f"- Conflict clusters: `{report['summary'].get('conflict_cluster_count', 0)}`",
        f"- Conflict pairs compared: `{report['summary'].get('conflict_pairs_compared', 0)}`",
        f"- Conflict pairs skipped: `{report['summary'].get('conflict_pairs_skipped', 0)}`",
        "",
    ]
    if report["summary"].get("llm_summary"):
        lines.append("## LLM Synthesis")
        lines.append("")
        lines.append(report["summary"]["llm_summary"])
        lines.append("")
    for item in report["skills"]:
        lines.append(f"## {item['skill']['name']}")
        lines.append("")
        lines.append(item["skill"]["description"] or "_No description detected._")
        lines.append("")
        lines.append(
            f"- Scores: discoverability `{item['scores']['discoverability']}`, "
            f"specificity `{item['scores']['specificity']}`, risk `{item['scores']['risk']}`"
        )
        lines.append(
            f"- Metrics: tokens `{item['metrics']['total_tokens_estimate']}`, "
            f"restrictions `{item['metrics']['restriction_count']}`, "
            f"examples `{item['metrics']['example_count']}`"
        )
        if item["findings"]:
            lines.append("- Findings:")
            for finding in item["findings"]:
                source = finding.get("source", "static")
                lines.append(
                    f"  - [{finding['severity']}][{source}] {finding['code']}: {finding['message']}"
                )
        else:
            lines.append("- Findings: none")
        rewrite = item.get("rewrite", {})
        if rewrite:
            lines.append(f"- {rewrite.get('headline', 'Suggested rewrite')}:")
            if rewrite.get("rewritten_description"):
                lines.append(f"  - Description: {rewrite['rewritten_description']}")
            cleanup_actions = rewrite.get("cleanup_actions", [])
            if cleanup_actions:
                lines.append(f"  - Cleanup: {'; '.join(cleanup_actions)}")
        lines.append("")
    if report.get("conflicts"):
        lines.append("## Conflicts")
        lines.append("")
        for conflict in report["conflicts"]:
            source = conflict.get("source", "static")
            lines.append(
                f"- [{conflict['severity']}][{source}] {conflict['category']} "
                f"(priority `{conflict.get('priority', 0)}`): "
                f"{conflict['left_skill']} vs {conflict['right_skill']}"
            )
            if conflict.get("cluster_id"):
                lines.append(
                    f"  - Cluster: {conflict['cluster_id']} "
                    f"(size `{conflict.get('cluster_size', 0)}`; "
                    f"context `{conflict.get('comparison_context', 'full-scan')}`)"
                )
            if conflict.get("recommendation"):
                lines.append(f"  - Recommendation: {conflict['recommendation']}")
    elif "conflicts" in report:
        lines.append("## Conflicts")
        lines.append("")
        lines.append("- None")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_summary(report: dict) -> str:
    worst = sorted(report["skills"], key=lambda item: item["scores"]["risk"], reverse=True)
    requested_policy_pack = report["summary"].get(
        "requested_policy_pack",
        report["profile"].get(
            "requested_policy_pack",
            report["profile"].get("policy_pack", "generic-agentic"),
        ),
    )
    policy_resolution = report["summary"].get(
        "policy_resolution",
        report["profile"].get("policy_resolution", "default"),
    )
    lines = [
        f"skills={report['summary']['skill_count']}",
        f"findings={report['summary']['finding_count']}",
        f"conflicts={report['summary'].get('conflict_count', len(report.get('conflicts', [])))}",
        f"requested_policy_pack={requested_policy_pack}",
        f"policy_resolution={policy_resolution}",
        f"rules_version={report['summary'].get('rules_version', 'generic-agentic@1.0')}",
        f"prompt_version={report['summary'].get('prompt_version', 'generic-agentic@1.0')}",
        f"llm_provider={report['summary'].get('llm_provider', 'none')}",
        f"llm_findings={report['summary'].get('llm_finding_count', 0)}",
        f"llm_conflicts={report['summary'].get('llm_conflict_count', 0)}",
        f"highest_conflict_priority={report['summary'].get('highest_conflict_priority', 0)}",
        f"conflict_clusters={report['summary'].get('conflict_cluster_count', 0)}",
        f"conflict_pairs_compared={report['summary'].get('conflict_pairs_compared', 0)}",
        f"conflict_pairs_skipped={report['summary'].get('conflict_pairs_skipped', 0)}",
    ]
    if worst:
        lines.append(f"highest_risk={worst[0]['skill']['name']}:{worst[0]['scores']['risk']}")
    return "\n".join(lines) + "\n"


def render_diff_markdown(diff: dict) -> str:
    lines = [
        "# Skill Auditor Diff",
        "",
        f"- Schema version: `{diff['schema_version']}`",
        f"- Generated at: `{diff['generated_at']}`",
        f"- Left: `{diff['comparison']['left']}`",
        f"- Right: `{diff['comparison']['right']}`",
        f"- Added skills: `{diff['summary']['added_skills']}`",
        f"- Removed skills: `{diff['summary']['removed_skills']}`",
        f"- Changed skills: `{diff['summary']['changed_skills']}`",
        f"- Improved skills: `{diff['summary']['improved_skills']}`",
        f"- Regressed skills: `{diff['summary']['regressed_skills']}`",
        f"- Conflict delta: `{diff['summary']['conflict_delta']}`",
        "",
    ]
    if not diff["skills"]:
        lines.append("## Skill Changes")
        lines.append("")
        lines.append("- None")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Skill Changes")
    lines.append("")
    for item in diff["skills"]:
        lines.append(
            f"- `{item['name']}`: `{item['status']}` "
            f"(risk delta `{item['risk_delta']}`, "
            f"finding delta `{item['finding_count_delta']}`)"
        )
        if item["added_findings"]:
            lines.append(f"  - Added findings: {', '.join(item['added_findings'])}")
        if item["removed_findings"]:
            lines.append(f"  - Removed findings: {', '.join(item['removed_findings'])}")
        if item["score_deltas"]:
            score_bits = ", ".join(
                f"{key} {value:+.2f}" for key, value in sorted(item["score_deltas"].items())
            )
            lines.append(f"  - Score deltas: {score_bits}")
        if item["metric_deltas"]:
            metric_bits = ", ".join(
                f"{key} {value:+.2f}" for key, value in sorted(item["metric_deltas"].items())
            )
            lines.append(f"  - Metric deltas: {metric_bits}")
    lines.append("")
    return "\n".join(lines)


def render_diff_summary(diff: dict) -> str:
    lines = [
        f"left={diff['comparison']['left']}",
        f"right={diff['comparison']['right']}",
        f"added_skills={diff['summary']['added_skills']}",
        f"removed_skills={diff['summary']['removed_skills']}",
        f"changed_skills={diff['summary']['changed_skills']}",
        f"improved_skills={diff['summary']['improved_skills']}",
        f"regressed_skills={diff['summary']['regressed_skills']}",
        f"conflict_delta={diff['summary']['conflict_delta']}",
    ]
    if diff["skills"]:
        most_changed = max(diff["skills"], key=lambda item: abs(item["risk_delta"]))
        lines.append(
            f"largest_risk_delta={most_changed['name']}:{most_changed['risk_delta']:+.2f}"
        )
    return "\n".join(lines) + "\n"

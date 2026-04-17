from __future__ import annotations


def render_markdown(report: dict) -> str:
    conflict_count = report["summary"].get("conflict_count", len(report.get("conflicts", [])))
    lines = [
        "# Skill Auditor Report",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Generated at: `{report['generated_at']}`",
        f"- Skills audited: `{report['summary']['skill_count']}`",
        f"- Findings: `{report['summary']['finding_count']}`",
        f"- Requested policy pack: `{report['profile'].get('requested_policy_pack', report['profile'].get('policy_pack', 'generic-agentic'))}`",
        f"- Policy pack: `{report['profile'].get('policy_pack', 'generic-agentic')}`",
        f"- Policy resolution: `{report['profile'].get('policy_resolution', report['summary'].get('policy_resolution', 'default'))}`",
        f"- Rules version: `{report['summary'].get('rules_version', 'generic-agentic@1.0')}`",
        f"- Prompt version: `{report['summary'].get('prompt_version', 'generic-agentic@1.0')}`",
        f"- LLM provider: `{report['summary'].get('llm_provider', 'none')}`",
        f"- LLM findings: `{report['summary'].get('llm_finding_count', 0)}`",
        f"- LLM conflicts: `{report['summary'].get('llm_conflict_count', 0)}`",
        f"- Conflicts: `{conflict_count}`",
        f"- Highest conflict priority: `{report['summary'].get('highest_conflict_priority', 0)}`",
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
        lines.append("")
    if report.get("conflicts"):
        lines.append("## Conflicts")
        lines.append("")
        for conflict in report["conflicts"]:
            lines.append(
                f"- [{conflict['severity']}][{conflict.get('source', 'static')}] {conflict['category']} "
                f"(priority `{conflict.get('priority', 0)}`): "
                f"{conflict['left_skill']} vs {conflict['right_skill']}"
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
    lines = [
        f"skills={report['summary']['skill_count']}",
        f"findings={report['summary']['finding_count']}",
        f"conflicts={report['summary'].get('conflict_count', len(report.get('conflicts', [])))}",
        f"requested_policy_pack={report['summary'].get('requested_policy_pack', report['profile'].get('requested_policy_pack', report['profile'].get('policy_pack', 'generic-agentic')))}",
        f"policy_resolution={report['summary'].get('policy_resolution', report['profile'].get('policy_resolution', 'default'))}",
        f"rules_version={report['summary'].get('rules_version', 'generic-agentic@1.0')}",
        f"prompt_version={report['summary'].get('prompt_version', 'generic-agentic@1.0')}",
        f"llm_provider={report['summary'].get('llm_provider', 'none')}",
        f"llm_findings={report['summary'].get('llm_finding_count', 0)}",
        f"llm_conflicts={report['summary'].get('llm_conflict_count', 0)}",
        f"highest_conflict_priority={report['summary'].get('highest_conflict_priority', 0)}",
    ]
    if worst:
        lines.append(f"highest_risk={worst[0]['skill']['name']}:{worst[0]['scores']['risk']}")
    return "\n".join(lines) + "\n"

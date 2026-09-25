from backend.models.simulation import StageData


def check_stage_rules(data: StageData, context: dict) -> list[str]:
    issues = []
    fact_ids = {fact["id"] for fact in context["facts"]}

    if not data.end_time_text.strip():
        issues.append("阶段停止时间不能为空")
    if data.end_reason == "target" and data.end_time_text != context["target_date"]:
        issues.append("抵达终点时，停止时间必须等于分支固定的终点日期")
    if data.end_reason == "choice" and data.end_time_text == context["target_date"]:
        issues.append("已抵达整体终点，应结束推演，不再创建待决定节点")

    for index, event in enumerate(data.events, start=1):
        if not event.summary.strip():
            issues.append(f"第 {index} 个事件缺少事件概述")
        if not event.mechanism.strip():
            issues.append(f"第 {index} 个事件缺少发生机制")
        unknown = set(event.fact_ids) - fact_ids
        if unknown:
            issues.append(
                f"第 {index} 个事件引用了上下文之外的事实节点："
                + "、".join(sorted(unknown))
            )

    if data.choice is not None:
        if not data.choice.situation.strip():
            issues.append("选择节点缺少需要作出决定的具体处境")
        options = [option.strip() for option in data.choice.options]
        if any(not option for option in options):
            issues.append("选择节点的选项不能为空")
        if len(set(options)) != len(options):
            issues.append("选择节点的选项不能重复")

    return issues
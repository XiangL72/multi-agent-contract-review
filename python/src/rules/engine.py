# Modified for the English text/TXT demo; scope and behavior are documented in README.md.
"""Optional composable drafting-rule utility; not a legal validity checker."""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class RuleOperator(str, Enum):
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    MATCHES = "matches"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    EQUALS = "eq"
    IN = "in"
    AND = "and"
    OR = "or"


class RuleSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Condition:
    """Condition."""
    field: str
    operator: RuleOperator
    value: Any
    sub_conditions: list["Condition"] = field(default_factory=list)

    def evaluate(self, context: dict) -> bool:
        if self.operator == RuleOperator.AND:
            return all(c.evaluate(context) for c in self.sub_conditions)
        if self.operator == RuleOperator.OR:
            return any(c.evaluate(context) for c in self.sub_conditions)

        actual = context.get(self.field, "")
        if isinstance(actual, str):
            actual_lower = actual.lower()
        else:
            actual_lower = actual

        if self.operator == RuleOperator.CONTAINS:
            return str(self.value).casefold() in str(actual).casefold()
        if self.operator == RuleOperator.NOT_CONTAINS:
            return str(self.value).casefold() not in str(actual).casefold()
        if self.operator == RuleOperator.MATCHES:
            return bool(re.search(self.value, str(actual), re.I))
        if self.operator == RuleOperator.GREATER_THAN:
            return float(actual) > float(self.value)
        if self.operator == RuleOperator.LESS_THAN:
            return float(actual) < float(self.value)
        if self.operator == RuleOperator.EQUALS:
            return str(actual) == str(self.value)
        if self.operator == RuleOperator.IN:
            return str(actual) in self.value

        return False


@dataclass
class Rule:
    """Rule."""
    id: str
    name: str
    description: str
    condition: Condition
    severity: RuleSeverity
    category: str
    action: str
    priority: int = 0
    enabled: bool = True
    metadata: dict = field(default_factory=dict)


@dataclass
class RuleResult:
    """Rule result."""
    rule_id: str
    rule_name: str
    matched: bool
    severity: RuleSeverity
    message: str
    action: str
    metadata: dict = field(default_factory=dict)


class RuleEngine:
    """Rule engine."""

    def __init__(self):
        self._rules: dict[str, Rule] = {}
        self._actions: dict[str, Callable] = {}
        self._load_default_rules()

    def register_rule(self, rule: Rule) -> None:
        self._rules[rule.id] = rule
        logger.debug("Registered rule: %s (%s)", rule.id, rule.name)

    def register_action(self, name: str, func: Callable) -> None:
        self._actions[name] = func

    def remove_rule(self, rule_id: str) -> None:
        self._rules.pop(rule_id, None)

    def evaluate(
        self,
        context: dict,
        category: str | None = None,
    ) -> list[RuleResult]:
        """Evaluate enabled rules in priority order with an optional category filter."""
        rules = sorted(self._rules.values(), key=lambda r: -r.priority)

        if category:
            rules = [r for r in rules if r.category == category]

        rules = [r for r in rules if r.enabled]

        results = []
        for rule in rules:
            matched = rule.condition.evaluate(context)
            if matched:
                results.append(
                    RuleResult(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        matched=True,
                        severity=rule.severity,
                        message=rule.description,
                        action=rule.action,
                        metadata=rule.metadata,
                    )
                )
        return results

    def evaluate_clause(self, clause_content: str, clause_title: str = "") -> list[RuleResult]:
        """Evaluate one clause and optional title with the rule utility."""
        context = {
            "content": clause_content,
            "title": clause_title,
            "full_text": f"{clause_title} {clause_content}",
        }
        return self.evaluate(context)

    def get_rules_by_category(self, category: str) -> list[Rule]:
        return [r for r in self._rules.values() if r.category == category]

    def get_statistics(self) -> dict:
        total = len(self._rules)
        by_severity = {}
        by_category = {}
        for r in self._rules.values():
            by_severity[r.severity.value] = by_severity.get(r.severity.value, 0) + 1
            by_category[r.category] = by_category.get(r.category, 0) + 1
        return {
            "total_rules": total,
            "by_severity": by_severity,
            "by_category": by_category,
        }

    def _load_default_rules(self) -> None:
        """Load optional English drafting heuristics, not legal validity rules."""
        default_rules = [
            Rule(
                id="R001",
                name="Unlimited liability check",
                description="Potential unlimited liability wording",
                condition=Condition(
                    field="", operator=RuleOperator.OR,
                    value=None,
                    sub_conditions=[
                        Condition("content", RuleOperator.CONTAINS, "unlimited liability"),
                        Condition("content", RuleOperator.CONTAINS, "bears all losses"),
                        Condition("content", RuleOperator.CONTAINS, "no liability cap"),
                        Condition("content", RuleOperator.CONTAINS, "uncapped damages"),
                    ],
                ),
                severity=RuleSeverity.CRITICAL,
                category="liability",
                action="flag_high_risk",
                priority=100,
            ),
            Rule(
                id="R002",
                name="Unilateral termination check",
                description="Potential unilateral termination wording",
                condition=Condition(
                    field="", operator=RuleOperator.OR,
                    value=None,
                    sub_conditions=[
                        Condition("content", RuleOperator.CONTAINS, "unilaterally terminate"),
                        Condition("content", RuleOperator.CONTAINS, "unilaterally end"),
                        Condition("content", RuleOperator.CONTAINS, "may terminate at any time"),
                        Condition("content", RuleOperator.CONTAINS, "terminate at will"),
                    ],
                ),
                severity=RuleSeverity.CRITICAL,
                category="termination",
                action="flag_high_risk",
                priority=95,
            ),
            Rule(
                id="R003",
                name="Penalty wording check",
                description="Penalty wording requires human review",
                condition=Condition(
                    field="", operator=RuleOperator.OR,
                    value=None,
                    sub_conditions=[
                        Condition("content", RuleOperator.MATCHES, r"penalty.*(?:three|3) times"),
                        Condition("content", RuleOperator.MATCHES, r"compensat.*all.*losses"),
                        Condition("content", RuleOperator.CONTAINS, "double damages"),
                    ],
                ),
                severity=RuleSeverity.WARNING,
                category="penalty",
                action="flag_medium_risk",
                priority=80,
            ),
            Rule(
                id="R004",
                name="Standard terms check",
                description="Potentially one-sided standard terms",
                condition=Condition(
                    field="", operator=RuleOperator.OR,
                    value=None,
                    sub_conditions=[
                        Condition("content", RuleOperator.CONTAINS, "excludes own liability"),
                        Condition("content", RuleOperator.CONTAINS, "excludes the other party principal rights"),
                        Condition("content", RuleOperator.CONTAINS, "increases the other party liability"),
                    ],
                ),
                severity=RuleSeverity.CRITICAL,
                category="validity",
                action="flag_invalid",
                priority=100,
                metadata={"basis": "drafting heuristic; no legal conclusion"},
            ),
            Rule(
                id="R005",
                name="Intellectual property check",
                description="Intellectual property ownership needs review",
                condition=Condition(
                    field="", operator=RuleOperator.OR,
                    value=None,
                    sub_conditions=[
                        Condition("content", RuleOperator.CONTAINS, "all intellectual property belongs to"),
                        Condition("content", RuleOperator.MATCHES, r"intellectual property.*irrevocabl.*assign"),
                        Condition("content", RuleOperator.CONTAINS, "waives all intellectual property"),
                    ],
                ),
                severity=RuleSeverity.WARNING,
                category="ip",
                action="flag_medium_risk",
                priority=85,
            ),
            Rule(
                id="R006",
                name="Confidentiality duration check",
                description="Confidentiality duration needs review",
                condition=Condition(
                    field="", operator=RuleOperator.OR,
                    value=None,
                    sub_conditions=[
                        Condition("content", RuleOperator.CONTAINS, "perpetual confidentiality"),
                        Condition("content", RuleOperator.CONTAINS, "confidentiality survives termination"),
                        Condition("content", RuleOperator.MATCHES, r"confidential.*(?:ten|10) years"),
                    ],
                ),
                severity=RuleSeverity.WARNING,
                category="confidentiality",
                action="flag_medium_risk",
                priority=70,
            ),
            Rule(
                id="R007",
                name="Automatic renewal check",
                description="Automatic renewal wording",
                condition=Condition(
                    field="", operator=RuleOperator.OR,
                    value=None,
                    sub_conditions=[
                        Condition("content", RuleOperator.CONTAINS, "renews automatically"),
                        Condition("content", RuleOperator.CONTAINS, "automatic renewal"),
                        Condition("content", RuleOperator.CONTAINS, "renews by default"),
                    ],
                ),
                severity=RuleSeverity.INFO,
                category="renewal",
                action="flag_attention",
                priority=50,
            ),
            Rule(
                id="R008",
                name="Ambiguous wording check",
                description="Potentially ambiguous wording",
                condition=Condition(
                    field="", operator=RuleOperator.OR,
                    value=None,
                    sub_conditions=[
                        Condition("content", RuleOperator.CONTAINS, "at its discretion"),
                        Condition("content", RuleOperator.CONTAINS, "subject to further agreement"),
                        Condition("content", RuleOperator.CONTAINS, "as circumstances require"),
                        Condition("content", RuleOperator.CONTAINS, "appropriate"),
                    ],
                ),
                severity=RuleSeverity.INFO,
                category="clarity",
                action="flag_attention",
                priority=40,
            ),
        ]

        for rule in default_rules:
            self.register_rule(rule)

        logger.info("Loaded %d default rules", len(default_rules))

from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import re


class Operator(str, Enum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX = "regex"


class ActionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    FLAG = "flag"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Condition(BaseModel):
    context_field: str = Field(..., description="The field from the request's context to check")
    operator: Operator = Field(..., description="The comparison operator")
    value: Union[str, int, float, bool, List[Union[str, int, float]]] = Field(..., description="The value to compare against")

    @field_validator('value')
    @classmethod
    def validate_value_type(cls, v, info):
        operator = info.data.get('operator')
        if operator in [Operator.IN, Operator.NOT_IN]:
            if not isinstance(v, list):
                raise ValueError(f"Value for operator '{operator}' must be a list")
        elif operator == Operator.REGEX:
            if not isinstance(v, str):
                raise ValueError(f"Value for operator '{operator}' must be a string")
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v


class Escalation(BaseModel):
    webhook_url: str = Field(..., description="URL to POST a notification to")
    severity: Severity = Field(default=Severity.INFO, description="Severity level of the escalation")


class RuleResult(BaseModel):
    action: ActionDecision = Field(..., description="The decision to take")
    message: str = Field(..., description="A reason for the decision")
    on_match: Optional[Escalation] = Field(None, description="Optional escalation configuration")


class Selector(BaseModel):
    agent_type: Optional[str] = Field(None, description="Type of agent (e.g., robot.vacuum)")
    agent_id: Optional[str] = Field(None, description="Specific agent instance ID (supports wildcards)")
    action_name: Optional[str] = Field(None, description="The action being performed")


class Rule(BaseModel):
    name: str = Field(..., description="Unique name for the rule")
    selector: Selector = Field(..., description="Conditions to determine if this rule applies")
    conditions: List[Condition] = Field(..., description="List of logical conditions that must all be true")
    result: RuleResult = Field(..., description="The outcome if selector and conditions match")


class PolicySpec(BaseModel):
    rules: List[Rule] = Field(..., description="List of rules in this policy")


class PolicyMetadata(BaseModel):
    name: str = Field(..., description="Unique name for the policy")
    description: str = Field(..., description="What the policy does")


class Policy(BaseModel):
    apiVersion: str = Field(default="aegis.io/v1", description="Version of the policy schema")
    kind: str = Field(default="Policy", description="Type of document")
    metadata: PolicyMetadata = Field(..., description="Policy metadata")
    spec: PolicySpec = Field(..., description="Policy specification")


class PolicyList(BaseModel):
    policies: List[Policy] = Field(..., description="List of policies")


# selector matching
def matches_selector(selector: Selector, agent_type: str, agent_id: str, action_name: str) -> bool:
    """check selector match"""

    # check type
    if selector.agent_type and selector.agent_type != agent_type:
        return False

    # check id (wildcards)
    if selector.agent_id:
        # wildcard: * = any chars
        pattern = selector.agent_id.replace('*', '.*')
        if not re.match(f'^{pattern}$', agent_id):
            return False

    # check action
    if selector.action_name and selector.action_name != action_name:
        return False

    return True


def evaluate_condition(condition: Condition, context_data: Dict[str, Any]) -> bool:
    """eval condition"""

    # navigate to field
    field_parts = condition.context_field.split('.')
    current_value = context_data

    try:
        for part in field_parts:
            if isinstance(current_value, dict):
                current_value = current_value.get(part)
            elif isinstance(current_value, list) and part.isdigit():
                current_value = current_value[int(part)]
            else:
                return False

        if current_value is None:
            return False

    except (KeyError, IndexError, TypeError):
        return False

    # apply operator
    expected_value = condition.value

    if condition.operator == Operator.EQ:
        return current_value == expected_value
    elif condition.operator == Operator.NEQ:
        return current_value != expected_value
    elif condition.operator == Operator.GT:
        return float(current_value) > float(expected_value)
    elif condition.operator == Operator.LT:
        return float(current_value) < float(expected_value)
    elif condition.operator == Operator.GTE:
        return float(current_value) >= float(expected_value)
    elif condition.operator == Operator.LTE:
        return float(current_value) <= float(expected_value)
    elif condition.operator == Operator.IN:
        return current_value in expected_value
    elif condition.operator == Operator.NOT_IN:
        return current_value not in expected_value
    elif condition.operator == Operator.CONTAINS:
        return expected_value in current_value
    elif condition.operator == Operator.NOT_CONTAINS:
        return expected_value not in current_value
    elif condition.operator == Operator.REGEX:
        return bool(re.search(expected_value, str(current_value)))

    return False

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from .policy import ActionDecision


class AgentInfo(BaseModel):
    type: str = Field(..., description="Type of agent (e.g., thermostat)")
    id: str = Field(..., description="Specific agent instance ID")
    ip_address: Optional[str] = Field(None, description="IP address of the agent")


class ActionParameters(BaseModel):
    """Flexible container for action parameters"""
    pass


class Action(BaseModel):
    name: str = Field(..., description="Name of the action being performed")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the action")


class EnvironmentContext(BaseModel):
    time_of_day_utc: Optional[str] = Field(None, description="Current time in UTC")
    location: Optional[str] = Field(None, description="Physical location context")
    is_occupied: Optional[bool] = Field(None, description="Whether the location is occupied")


class OriginatorInfo(BaseModel):
    type: str = Field(..., description="Type of originator (user, service, etc.)")
    id: str = Field(..., description="ID of the originator")


class RequestContext(BaseModel):
    environment: Optional[EnvironmentContext] = Field(None, description="Environmental context")
    originator: Optional[OriginatorInfo] = Field(None, description="Information about the request originator")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Additional custom context fields")


class EvaluationRequest(BaseModel):
    request_id: str = Field(..., description="Unique ID for this evaluation request")
    agent: AgentInfo = Field(..., description="Information about the agent")
    action: Action = Field(..., description="The action to be evaluated")
    context: RequestContext = Field(..., description="Context information for policy evaluation")


class EvaluationResponse(BaseModel):
    request_id: str = Field(..., description="Unique ID matching the request")
    decision: ActionDecision = Field(..., description="The decision made by the policy engine")
    reason: Optional[str] = Field(None, description="Reason for the decision")
    matched_policy: Optional[str] = Field(None, description="Name of the policy that made the decision")
    matched_rule: Optional[str] = Field(None, description="Name of the rule that made the decision")
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Timestamp of the decision")
    latency_ms: int = Field(..., description="Processing latency in milliseconds")


class PolicyCreateRequest(BaseModel):
    policy_yaml: str = Field(..., description="YAML policy definition")


class PolicyUpdateRequest(BaseModel):
    policy_yaml: str = Field(..., description="Updated YAML policy definition")


class PolicyResponse(BaseModel):
    name: str = Field(..., description="Policy name")
    policy_yaml: str = Field(..., description="YAML policy definition")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code for programmatic handling")
    request_id: Optional[str] = Field(None, description="Request ID if available")
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Timestamp of the error")

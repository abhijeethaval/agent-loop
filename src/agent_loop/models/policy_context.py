"""Policy context model.

Defines the static policy context with explicit precedence.
"""

from pydantic import BaseModel, Field


class PolicyContext(BaseModel):
    """Static policy context for decision making.
    
    Precedence Order (encoded as instruction in DSPy signature):
    1. Organization policies (highest priority)
    2. Industry / regulatory rules
    3. Domain guidelines
    4. User goal (lowest priority)
    
    Policy precedence is instruction-level; policy content is data-level.
    """
    org_policies: str = Field(
        default="",
        description="Organization-level policies that override all other inputs"
    )
    industry_rules: str = Field(
        default="",
        description="Industry or regulatory rules that override domain guidelines"
    )
    domain_guidelines: str = Field(
        default="",
        description="Domain-specific guidelines for the task"
    )

from typing import Optional
from pydantic import BaseModel, Field


class SerpApiBalanceResponse(BaseModel):
    """Account status, quota, and searches balance from SerpAPI."""
    account_email: Optional[str] = Field(None, description="SerpAPI account email")
    plan_name: Optional[str] = Field(None, description="Plan tier name")
    total_searches_left: Optional[int] = Field(None, description="Total remaining searches including extra credits")
    plan_searches_left: Optional[int] = Field(None, description="Remaining searches on current monthly plan")
    searches_per_month: Optional[int] = Field(None, description="Monthly plan search quota")
    this_month_usage: Optional[int] = Field(None, description="Searches used this current month")
    this_hour_searches: Optional[int] = Field(None, description="Searches performed this hour")
    account_rate_limit_per_hour: Optional[int] = Field(None, description="Maximum searches allowed per hour")
    plan_renewal_date: Optional[str] = Field(None, description="Subscription renewal date")

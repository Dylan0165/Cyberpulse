"""Commercial plan tiers — single source of truth for limits and pricing.

Plans: trial (free after registration) | starter | business | enterprise | admin
Limits are ALWAYS enforced server-side; the frontend only shows warnings.
"""

UNLIMITED_SCANS = 999  # max_scans_per_month >= this means "unlimited"

PLAN_LIMITS: dict[str, dict] = {
    "trial":      {"max_targets": 1,    "max_scans_per_month": 1,      "custom_modules": False, "scheduled_scans": False, "white_label": False, "ai_upgrade": "deepseek"},
    "starter":    {"max_targets": 1,    "max_scans_per_month": 1,      "custom_modules": False, "scheduled_scans": False, "white_label": False, "ai_upgrade": "deepseek"},
    "business":   {"max_targets": 5,    "max_scans_per_month": 999,    "custom_modules": True,  "scheduled_scans": True,  "white_label": False, "ai_upgrade": "deepseek"},
    "enterprise": {"max_targets": 20,   "max_scans_per_month": 999,    "custom_modules": True,  "scheduled_scans": True,  "white_label": True,  "ai_upgrade": "choice"},
    "admin":      {"max_targets": 9999, "max_scans_per_month": 999999, "custom_modules": True,  "scheduled_scans": True,  "white_label": True,  "ai_upgrade": "choice"},
}

# Monthly-equivalent price in EUR (for the admin revenue estimate).
PLAN_MONTHLY_PRICE: dict[str, int] = {
    "trial": 0, "starter": 149, "business": 349, "enterprise": 799, "admin": 0,
}


def apply_plan_limits(user, plan: str) -> None:
    """Apply a plan's feature limits to a user in place. Unknown → trial."""
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["trial"])
    user.plan = plan
    user.max_targets = limits["max_targets"]
    user.max_scans_per_month = limits["max_scans_per_month"]
    user.custom_modules = limits["custom_modules"]
    user.scheduled_scans = limits["scheduled_scans"]
    user.white_label = limits["white_label"]
    user.ai_upgrade = limits["ai_upgrade"]


def is_unlimited(max_scans: int | None) -> bool:
    return (max_scans or 0) >= UNLIMITED_SCANS

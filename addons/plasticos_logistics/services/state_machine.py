VALID_TRANSITIONS = {
    "draft": ["awaiting_ready"],
    "awaiting_ready": ["ready_confirmed"],
    "ready_confirmed": ["rate_confirmed"],
    "rate_confirmed": ["scheduled"],
    "scheduled": ["dispatched"],
    "dispatched": ["picked_up"],
    "picked_up": ["delivered"],
    "delivered": ["closed"],
}

"""Shared software guardrails; hardware capacity is measured separately."""
MAX_PARALLEL=4
MAX_CONTEXT=65536
MAX_TOTAL_CONTEXT=65536
MAX_OUTPUT=8192
MIN_CONTEXT=2048
DEFAULT_OUTPUT=800

def output_limit(context,requested):
    return min(requested,max(256,context//4))

def budget(context,parallel,requested):
    effective=output_limit(context,requested)
    return dict(context_per_slot=context,context_total=context*parallel,requested_output_per_slot=requested,effective_output_per_slot=effective,max_output_all_slots=parallel*effective,slots=[dict(slot=i+1,context=context,max_output=effective) for i in range(parallel)])

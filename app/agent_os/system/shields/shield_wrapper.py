from agent_os.system.shields.shield_runtime import (
    shield_pre,
    shield_post
)


async def run_shielded(node_fn, state, config):

    # ======================
    # PRE-GUARD
    # ======================
    clean_input = shield_pre(state["user_input"])

    state["user_input"] = clean_input

    # ======================
    # NODE EXECUTION
    # ======================
    raw_output = await node_fn(state, config)

    # ======================
    # POST-GUARD
    # ======================
    safe_output = shield_post(raw_output)

    return {
        "ads_output": safe_output
    }

async def run_shielded(node_name, state, config, fn):
    
    # PRE
    SHIELD.scrub(state.user_input)
    POLICY.check(node_name)
    BUDGET.check(state)

    # EXECUTE NODE
    result = await fn(state, config)

    # POST
    SHIELD.validate_output(result)
    TELEMETRY.log(node_name, result)

    return result
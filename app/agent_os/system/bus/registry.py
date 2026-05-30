class BusRegistry:


    IG = "input_guard"

    SV = "supervisor"

    MT = "marketing"

    KL = "knowledge"

    LWC = "lightweight_chat"

    EV = "evaluator"
    
    AG = "aggregator"

    OG = "output_guard"

    HR = "human_review"
    
    SS = "shared_state"

    FR = "final_response"

    UI = "ui_selector"

    RS = "result_store"

    RO = "heuristic_router"

    CR = "cache_read"

    CW = "cache_write"

    KLB = "knowledge_base"

    RC =  "relevance_check"

    LLM =  "llm_generation"

    FB =  "fallback_search"

    GEN =  "generation"


    

    # =====================================================
    # INTERNAL ORCHESTRATION
    # =====================================================

    TRACE = "reg_execution_trace"

    METRICS = "reg_metrics"

    HEALTH = "reg_system_health"
    

    # =====================================================
    # UTILITY
    # =====================================================

    @classmethod
    def all_slots(cls) -> list[str]:
        """
        Auto-discover toàn bộ register trên mainboard
        """

        return [

            value

            for key, value in cls.__dict__.items()

            if (
                isinstance(value, str)
                and key.isupper()
            )
        ]

    @classmethod
    def orchestration_slots(cls) -> list[str]:
        """
        Các slot điều phối workflow
        """

        return [

            cls.BS,
            cls.IS,
            cls.EB,
            cls.TRACE,
        ]

    @classmethod
    def observability_slots(cls) -> list[str]:
        """
        Các slot monitoring / audit / debug
        """

        return [

            cls.AL,
            cls.OBS,
            cls.METRICS,
            cls.HEALTH,
        ]

    @classmethod
    def protection_slots(cls) -> list[str]:
        """
        Các slot bảo vệ production runtime
        """

        return [

            cls.RL,
            cls.CB,
            cls.DLQ,
        ]
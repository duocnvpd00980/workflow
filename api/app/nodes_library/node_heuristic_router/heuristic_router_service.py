# heuristic_router_service.py

from pathlib import Path
import re
import yaml

from .heuristic_router_protocol import HeuristicRouterOutput


class HeuristicRouterService:
    def __init__(self):

        config_path = Path(__file__).parent / "router_patterns.yml"

        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        self.routes = {}

        for route_name, cfg in raw.items():
            keywords = [k.strip().lower() for k in cfg.get("keywords", [])]

            regex_patterns = [
                re.compile(p, re.IGNORECASE) for p in cfg.get("regex", [])
            ]

            self.routes[route_name] = {
                "keywords": keywords,
                "regex": regex_patterns,
            }

    def run(self, query: str) -> HeuristicRouterOutput:

        normalized = query.strip().lower()

        for route_name, cfg in self.routes.items():
            # keyword match
            for keyword in cfg["keywords"]:
                if keyword in normalized:
                    return HeuristicRouterOutput(
                        route=route_name,
                        matched_keyword=keyword,
                        query_snapshot=query,
                    )

            # regex fallback
            for pattern in cfg["regex"]:
                match = pattern.search(normalized)

                if match:
                    return HeuristicRouterOutput(
                        route=route_name,
                        matched_keyword=match.group(0),
                        query_snapshot=query,
                    )

        return HeuristicRouterOutput(
            route="general_chat",
            matched_keyword=None,
            query_snapshot=query,
        )

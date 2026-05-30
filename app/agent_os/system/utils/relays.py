from langgraph.graph import END

class Relay:
    def __init__(self, mapping, signal_field="router_decision"):
        self.mapping = mapping
        self.signal_field = signal_field
        self.__name__ = "RelaySwitch"

    def __call__(self, state):
        # Đọc tín hiệu từ Bus
        signal = getattr(state, self.signal_field, "invalid")
        return self.mapping.get(signal, "invalid")

    def wire(self, workflow, source_node):
        """Hàm này tự động 'hàn' dây và cung cấp sơ đồ cho Mermaid"""
        workflow.add_conditional_edges(source_node, self, self.mapping)
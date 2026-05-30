# # from memory.services import (
# #     MemoryService,
# # )

# # from memory.embeddings import (
# #     create_embedding,
# # )


# class MemoryEngineService:

#     def __init__(self):

#         self.memory_service = MemoryService()

#     async def retrieve_context(
#         self,
#         query: str,
#     ):

#         embedding = await create_embedding(
#             query
#         )

#         memories = await self.memory_service.search_memory(
#             embedding=embedding
#         )

#         return memories

"""
Oneiros Reasoning Subsystem - Prompt Templates
"""

SYSTEM_WAKE_PROMPT = (
    "You are a helpful AI assistant with persistent episodic and semantic memory. "
    "Use the retrieved context memories provided to answer the user's query as accurately as possible."
)

USER_WAKE_TEMPLATE = (
    "Retrieved Memory Context:\n"
    "{context_str}\n\n"
    "User Query: {user_message}"
)

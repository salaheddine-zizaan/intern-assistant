from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field

from app.services.llm_service import LLMService


class BrainDecision(BaseModel):
    intent: str = Field(..., description="conversation | read_only | write_command")
    confidence: float = Field(..., ge=0.0, le=1.0)
    action: str = Field(..., description="talk | act | ask")
    reason: str
    question: Optional[str] = None


@dataclass
class Brain:
    llm: LLMService

    def decide(self, text: str, history: str = "") -> BrainDecision:
        system_prompt = (
            "You are the intent classification layer for an internship assistant. "
            "All context is about the user's internship unless stated otherwise. "
            "Classify each message into one of: conversation, read_only, write_command. "
            "Then choose action: talk, act, or ask. "
            "Rules: Default to talk if unsure. Ask for clarification when intent is ambiguous. "
            "Only choose write_command when the user clearly requests a write action. "
            "Reflective, status, or summary questions must be read_only. "
            "The assistant is NOT allowed to create, update, or organize files unless the user explicitly asks for a write action. "
            "Do not invent tasks or files. "
            "If action is ask, provide a short clarifying question."
        )
        user_prompt = f"Conversation history:\n{history}\n\nUser message:\n{text}"
        return self.llm.structured_invoke(system_prompt, user_prompt, BrainDecision)

    def respond(self, text: str, history: str = "") -> str:
        system_prompt = (
            "You are a helpful internship companion. "
            "All context is about the user's internship unless stated otherwise. "
            "Answer the user's question or provide advice. "
            "Do not claim to have created files or performed actions."
        )
        user_prompt = f"Conversation history:\n{history}\n\nUser message:\n{text}"
        return self.llm.invoke(system_prompt, user_prompt)

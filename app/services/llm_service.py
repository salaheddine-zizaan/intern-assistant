from __future__ import annotations

from typing import Type, TypeVar

import sys
import os
from getpass import getpass
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from app.services.config_service import ConfigService


T = TypeVar("T")


class LLMService:
    def __init__(self, api_key: str | None, model: str, config_path: str | None = None):
        self.model_name = model
        self.api_key = api_key
        self.config = ConfigService(Path(config_path) if config_path else Path(".env.local"))
        if self._is_ollama_model(model):
            self.provider = "ollama"
            self.model = self._build_ollama_model(model)
        else:
            if not api_key:
                raise RuntimeError("GOOGLE_API_KEY is required to run the LLM service.")
            self.provider = "gemini"
            self.model = ChatGoogleGenerativeAI(
                model=model, google_api_key=api_key, temperature=0.2
            )

    def set_model(self, model_name: str) -> None:
        if not model_name or model_name == self.model_name:
            return
        self.model_name = model_name
        if self._is_ollama_model(model_name):
            self.provider = "ollama"
            self.model = self._build_ollama_model(model_name)
        else:
            if not self.api_key:
                raise RuntimeError("GOOGLE_API_KEY is required to run the LLM service.")
            self.provider = "gemini"
            self.model = ChatGoogleGenerativeAI(
                model=model_name, google_api_key=self.api_key, temperature=0.2
            )

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        prompt = ChatPromptTemplate.from_messages(
            [("system", "{system}"), ("user", "{user}")]
        )
        chain = prompt | self.model
        content = self._invoke_chain(chain, system_prompt, user_prompt)
        return self._normalize_content(content)

    def structured_invoke(self, system_prompt: str, user_prompt: str, output_model: Type[T]) -> T:
        parser = PydanticOutputParser(pydantic_object=output_model)
        prompt = ChatPromptTemplate.from_messages(
            [("system", "{system}"), ("user", "{user}")]
        )
        chain = prompt | self.model
        augmented_user = f"{user_prompt}\n\n{parser.get_format_instructions()}"
        content = self._invoke_chain(chain, system_prompt, augmented_user)
        normalized = self._normalize_content(content)
        return parser.parse(normalized)

    def _invoke_chain(self, chain, system_prompt: str, user_prompt: str):
        try:
            result = chain.invoke({"system": system_prompt, "user": user_prompt})
            return result.content
        except Exception as exc:
            if self.provider == "ollama" and self._is_ollama_not_available(exc):
                raise RuntimeError(
                    "OLLAMA_NOT_AVAILABLE: Ollama is not running or not installed."
                ) from exc
            if self._is_model_not_found(exc):
                if self.model_name != "gemini-1.5-flash-001":
                    self.set_model("gemini-1.5-flash-001")
                    refreshed_chain = (
                        ChatPromptTemplate.from_messages(
                            [("system", "{system}"), ("user", "{user}")]
                        )
                        | self.model
                    )
                    result = refreshed_chain.invoke(
                        {"system": system_prompt, "user": user_prompt}
                    )
                    return result.content
            if self._is_auth_error(exc):
                if self._refresh_api_key():
                    refreshed_chain = (
                        ChatPromptTemplate.from_messages(
                            [("system", "{system}"), ("user", "{user}")]
                        )
                        | self.model
                    )
                    result = refreshed_chain.invoke(
                        {"system": system_prompt, "user": user_prompt}
                    )
                    return result.content
            raise

    def _is_model_not_found(self, exc: Exception) -> bool:
        text = str(exc)
        return "NOT_FOUND" in text and "models/" in text

    def _is_auth_error(self, exc: Exception) -> bool:
        text = str(exc).lower()
        return "api key" in text or "unauthorized" in text or "permission" in text

    def _is_ollama_not_available(self, exc: Exception) -> bool:
        text = str(exc).lower()
        return (
            "connection refused" in text
            or "connecterror" in text
            or "failed to establish a new connection" in text
        )

    def _refresh_api_key(self) -> bool:
        if not (hasattr(sys, "stdin") and sys.stdin and sys.stdin.isatty()):
            return False
        try:
            new_key = getpass("Gemini API key invalid. Enter a new key: ").strip()
        except EOFError:
            return False
        if not new_key:
            return False
        if not self._validate_key(new_key):
            return False
        self.api_key = new_key
        if self.provider == "gemini":
            self.model = ChatGoogleGenerativeAI(
                model=self.model_name, google_api_key=new_key, temperature=0.2
            )
        self.config.save({"GOOGLE_API_KEY": new_key})
        return True

    def _validate_key(self, key: str) -> bool:
        try:
            model = ChatGoogleGenerativeAI(model=self.model_name, google_api_key=key)
            model.invoke("ping")
            return True
        except Exception:
            return False

    @staticmethod
    def _is_ollama_model(model_name: str) -> bool:
        return model_name.lower().startswith("ollama:")

    @staticmethod
    def _extract_ollama_model(model_name: str) -> str:
        _, _, name = model_name.partition(":")
        return name.strip() or "llama3.1"

    def _build_ollama_model(self, model_name: str):
        base_url = (
            self.config.load().get("OLLAMA_BASE_URL")
            or str(os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434")
        )
        return ChatOllama(model=self._extract_ollama_model(model_name), base_url=base_url)

    @staticmethod
    def _normalize_content(content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "\n".join(parts).strip()
        return str(content)

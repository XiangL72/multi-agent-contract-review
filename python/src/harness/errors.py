"""Allowlisted public errors; never format arbitrary exception payloads."""
from __future__ import annotations
import json
import logging
from .execution import ModelCallError

MESSAGES = {'TEXT_TOO_LONG': 'Contract text exceeds 15000 characters; truncation is prohibited',
 'RISK_CATEGORY_CONTRADICTION': 'Unlimited-liability category contradicts explicit capped-liability wording; review required',
 'SUGGESTION_FACT_LOSS': 'Proposed revision omits or changes a protected numeric value or quantity; review required',
 'EMPTY_EXTRACTION': 'Model did not return a valid nonempty clauses list',
 'UNSUPPORTED_CONTRACT_TYPE': 'Only purchase/sale contracts are supported',
 'INVALID_CLAUSE': 'Clause has no source content',
 'INVALID_SOURCE_SPAN': 'Model clause cannot be located in the source contract',
 'INVALID_SUGGESTIONS': 'Suggestion output has no suggestions list',
 'UNKNOWN_SUGGESTION_CLAUSE': 'Suggestion references an unknown clause ID',
 'INVALID_SUGGESTED_TEXT': 'Suggested text must be a nonempty string',
 'INVALID_COMPLIANCE_OUTPUT': 'Compliance output has no findings list',
 'UNKNOWN_COMPLIANCE_CLAUSE': 'Compliance finding references an unknown clause ID',
 'MISSING_COMPLIANCE_EVIDENCE': 'Compliance finding has no located source clause',
 'INVALID_RISK_OUTPUT': 'Risk output has no findings list',
 'UNKNOWN_RISK_CLAUSE': 'Risk finding references an unknown clause ID',
 'MISSING_RISK_EVIDENCE': 'Risk finding has no located source clause',
 'PROVIDER_NOT_CONFIGURED': 'Configure the selected provider API_KEY.',
 'INVALID_PROVIDER': 'LLM_PROVIDER must be auto, minimax, or openai (OpenAI-compatible).',
 'MODEL_NOT_CONFIGURED': 'Set LLM_MODEL for your OpenAI-compatible provider in python/.env.'}

class ReviewStageError(ValueError):
    def __init__(self, code: str):
        self.code = code if code in MESSAGES else "STAGE_ERROR"
        super().__init__(MESSAGES.get(self.code, "Review stage failed."))

_PROVIDER_CODES = frozenset({"TOTAL_TIMEOUT", "MODEL_TIMEOUT", "BUDGET_EXCEEDED",
    "AUTHENTICATION", "RATE_LIMIT", "NETWORK", "PROVIDER_ERROR", "PROVIDER_REJECTED", "MODEL_ERROR"})

def safe_stage_error(stage: str, exc: Exception, logger: logging.Logger) -> str:
    """Preserve trusted error codes without exception text or traceback payloads."""
    if isinstance(exc, ReviewStageError):
        code = exc.code
        message = MESSAGES.get(code, "Review stage failed.")
    elif isinstance(exc, ModelCallError):
        code = exc.code if exc.code in _PROVIDER_CODES else "MODEL_ERROR"
        message = "Model request did not complete successfully."
    elif isinstance(exc, json.JSONDecodeError):
        code, message = "INVALID_MODEL_JSON", "Model response is not valid JSON."
    elif isinstance(exc, (ValueError, TypeError, KeyError, AttributeError)):
        code, message = "INVALID_MODEL_OUTPUT", "Model output failed schema or source validation."
    else:
        code, message = "STAGE_ERROR", "Review stage failed."
    logger.warning("Review stage failed stage=%s code=%s", stage, code)
    return f"{code}: {message}"

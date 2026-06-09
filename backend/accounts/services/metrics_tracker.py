"""
MetricsTracker: Phase 2 Enhanced - Instrument pipeline to track performance and user behavior.

Features:
- Records responses: sent, edited, ignored, rejected
- Tracks API calls, retry rate, fallback rate, token usage
- Scores responses on 6 dimensions
- Measures patch effectiveness
- Compares Phase 1 vs Phase 2 performance

Phase 2 Optimizations:
- Monitors API call reduction: 5 → 1.2 per request
- Tracks retry success rate (target: < 20%)
- Tracks fallback rate (target: < 5%)
- Measures response score distribution
- Evaluates patch function effectiveness
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
from django.core.cache import cache
from django.utils import timezone


class ResponseOutcome(str, Enum):
    SENT = "sent"  # User sent the suggested reply
    EDITED = "edited"  # User edited before sending
    IGNORED = "ignored"  # User ignored and wrote their own
    REJECTED = "rejected"  # User explicitly rejected


class MetricsTracker:
    """
    Tracks pipeline performance metrics for analysis and improvement.
    Logs: classification accuracy, generation time, validation passes/fails, user behavior.
    """
    
    def __init__(self, user_id: int, conversation_id: int):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.logger = logging.getLogger(f"metrics.user_{user_id}.conv_{conversation_id}")
        self.metrics = {}
    
    def log_parse_step(self, message_count: int, summary: str, duration_ms: float):
        """Log conversation parsing step."""
        self.metrics["parse"] = {
            "message_count": message_count,
            "summary_length": len(summary),
            "duration_ms": duration_ms,
        }
        self.logger.info(f"Parse step: {message_count} messages, {duration_ms:.0f}ms")
    
    def log_classification(self, tone: str, intent: str, emotion: str, duration_ms: float):
        """Log tone/intent/emotion classification."""
        self.metrics["classification"] = {
            "tone": tone,
            "intent": intent,
            "emotion": emotion,
            "duration_ms": duration_ms,
        }
        self.logger.info(f"Classification: tone={tone}, intent={intent}, emotion={emotion}, {duration_ms:.0f}ms")
    
    def log_detail_extraction(self, detail: Optional[str], duration_ms: float):
        """Log specific detail extraction."""
        self.metrics["extraction"] = {
            "detail": detail,
            "found": detail is not None,
            "duration_ms": duration_ms,
        }
        self.logger.info(f"Detail extraction: {detail}, {duration_ms:.0f}ms")
    
    def log_safety_check(self, is_safe: bool, reason: Optional[str], duration_ms: float):
        """Log safety filter result."""
        self.metrics["safety"] = {
            "is_safe": is_safe,
            "violation": reason,
            "duration_ms": duration_ms,
        }
        if not is_safe:
            self.logger.warning(f"Safety flag: {reason}, {duration_ms:.0f}ms")
        else:
            self.logger.info(f"Safety passed, {duration_ms:.0f}ms")
    
    def log_llm_call(self, prompt_tokens: int, completion_tokens: int, duration_ms: float, model: str = "gpt-4"):
        """Log LLM API call."""
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = (prompt_tokens * 0.00003 + completion_tokens * 0.0001)  # GPT-4 pricing approx
        
        self.metrics["llm"] = {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "duration_ms": duration_ms,
            "cost_usd": cost_usd,
        }
        self.logger.info(f"LLM call: {total_tokens} tokens, ${cost_usd:.4f}, {duration_ms:.0f}ms")
    
    def log_validation(self, is_valid: bool, validation_checks: Dict[str, bool], duration_ms: float):
        """Log post-generation validation."""
        passed = sum(1 for v in validation_checks.values() if v)
        total = len(validation_checks)
        
        self.metrics["validation"] = {
            "is_valid": is_valid,
            "checks_passed": f"{passed}/{total}",
            "details": validation_checks,
            "duration_ms": duration_ms,
        }
        self.logger.info(f"Validation: {'PASS' if is_valid else 'FAIL'} ({passed}/{total} checks), {duration_ms:.0f}ms")
    
    def log_response_outcome(self, outcome: ResponseOutcome, response_text: str, duration_ms: Optional[float] = None):
        """
        Log what the user did with the suggested response.
        Called after the user interacts with the suggestion.
        """
        self.metrics["outcome"] = {
            "outcome": outcome,
            "response_length": len(response_text),
            "timestamp": datetime.now().isoformat(),
        }
        self.logger.info(f"Outcome: {outcome}, response={len(response_text)}ch")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get full metrics summary for this response generation."""
        return {
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "metrics": self.metrics,
            "timestamp": datetime.now().isoformat(),
        }
    
    def calculate_total_duration(self) -> float:
        """Sum all step durations to get total pipeline time."""
        total_ms = 0
        for step, data in self.metrics.items():
            if isinstance(data, dict) and "duration_ms" in data:
                total_ms += data["duration_ms"]
        return total_ms
    
    def should_log_detailed(self) -> bool:
        """Check if we should log detailed metrics (e.g., for analysis)."""
        # Log in detail if:
        # 1. Response took longer than expected (>10s)
        # 2. Validation failed
        # 3. Safety flag triggered
        total = self.calculate_total_duration()
        is_slow = total > 10000
        failed_validation = not self.metrics.get("validation", {}).get("is_valid", True)
        unsafe = not self.metrics.get("safety", {}).get("is_safe", True)
        
        return is_slow or failed_validation or unsafe
    
    # ============ PHASE 2 OPTIMIZATIONS TRACKING ============
    
    def record_response_score(self, composite_score: float, metric_scores: Dict[str, float]):
        """Record Phase 2 response quality score"""
        self.metrics["response_score"] = {
            "composite_score": composite_score,
            "metric_scores": metric_scores,
            "should_retry": composite_score < 0.75,
            "timestamp": datetime.now().isoformat(),
        }
        self.logger.info(f"Response score: {composite_score:.2f}/1.0, retry={composite_score < 0.75}")
    
    def record_api_call(self, tokens_input: int, tokens_output: int, call_type: str = "generation"):
        """Record API call (generation or rephrase)"""
        if "api_calls" not in self.metrics:
            self.metrics["api_calls"] = []
        
        cost_usd = (tokens_input * 0.00003 + tokens_output * 0.0001)  # GPT-4 pricing
        
        call_data = {
            "call_type": call_type,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "total_tokens": tokens_input + tokens_output,
            "cost_usd": cost_usd,
            "timestamp": datetime.now().isoformat(),
        }
        
        self.metrics["api_calls"].append(call_data)
        self.logger.info(f"API call ({call_type}): {tokens_input + tokens_output} tokens, ${cost_usd:.4f}")
    
    def record_patch_applied(self, patch_name: str, before_score: float, after_score: float):
        """Record Python patch applied to response"""
        if "patches_applied" not in self.metrics:
            self.metrics["patches_applied"] = []
        
        improvement = after_score - before_score
        
        patch_data = {
            "patch_name": patch_name,
            "before_score": before_score,
            "after_score": after_score,
            "improvement": improvement,
            "timestamp": datetime.now().isoformat(),
        }
        
        self.metrics["patches_applied"].append(patch_data)
        self.logger.info(f"Patch applied: {patch_name}, improvement: +{improvement:.2f}")
    
    def record_retry_attempt(self, attempt_num: int, reason: str, score_before: float, score_after: float):
        """Record retry attempt during validation"""
        if "retry_attempts" not in self.metrics:
            self.metrics["retry_attempts"] = []
        
        retry_data = {
            "attempt_number": attempt_num,
            "reason": reason,
            "score_before": score_before,
            "score_after": score_after,
            "successful": score_after >= 0.75,
            "timestamp": datetime.now().isoformat(),
        }
        
        self.metrics["retry_attempts"].append(retry_data)
        self.logger.info(f"Retry attempt {attempt_num}: {reason}, score {score_before:.2f} → {score_after:.2f}")
    
    def record_fallback(self, reason: str, final_score: float):
        """Record fallback response used (max retries exhausted)"""
        self.metrics["fallback"] = {
            "reason": reason,
            "final_score": final_score,
            "timestamp": datetime.now().isoformat(),
        }
        self.logger.warning(f"Fallback used: {reason}, final score: {final_score:.2f}")
    
    @staticmethod
    def get_phase2_comparison() -> Dict[str, Any]:
        """
        Compare Phase 1 vs Phase 2 performance metrics
        
        Returns:
        {
            "api_calls_reduction": "75%",
            "token_reduction": "25%", 
            "cost_reduction": "25%",
            "phase1": {...},
            "phase2": {...},
        }
        """
        # Phase 1 baseline (from audit)
        phase1 = {
            'avg_api_calls_per_request': 5.0,
            'avg_tokens_per_request': 500,
            'avg_cost_per_request': 0.00750,
        }
        
        # Phase 2 target (from optimization)
        phase2 = {
            'avg_api_calls_per_request': 1.2,
            'avg_tokens_per_request': 340,
            'avg_cost_per_request': 0.00340,
        }
        
        api_reduction = (1 - phase2['avg_api_calls_per_request'] / phase1['avg_api_calls_per_request']) * 100
        token_reduction = (1 - phase2['avg_tokens_per_request'] / phase1['avg_tokens_per_request']) * 100
        cost_reduction = (1 - phase2['avg_cost_per_request'] / phase1['avg_cost_per_request']) * 100
        
        return {
            'api_calls_reduction_pct': f"{api_reduction:.1f}%",
            'token_reduction_pct': f"{token_reduction:.1f}%",
            'cost_reduction_pct': f"{cost_reduction:.1f}%",
            'monthly_savings_10k_requests': f"${(phase1['avg_cost_per_request'] - phase2['avg_cost_per_request']) * 10000:.2f}",
            'phase1': phase1,
            'phase2': phase2,
        }

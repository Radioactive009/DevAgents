import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from .models import HealthCheckResult

class HealthCheckService:
    def __init__(self, request_fn=None):
        self._request_fn = request_fn or self._default_request_fn

    @staticmethod
    def _default_request_fn(url: str, timeout: int = 10) -> Tuple[int, bytes, float]:
        start = time.time()
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "DevAgents-Health-Checker/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                latency_ms = (time.time() - start) * 1000
                return resp.status, data, latency_ms
        except urllib.error.HTTPError as e:
            latency_ms = (time.time() - start) * 1000
            return e.code, e.read(), latency_ms
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return 0, str(e).encode("utf-8"), latency_ms

    def verify_deployment_health(
        self,
        deployment_url: str,
        expected_content: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 10
    ) -> HealthCheckResult:
        """
        Execute bounded smoke test against a live deployment URL.
        """
        if not deployment_url.startswith("http"):
            deployment_url = f"https://{deployment_url}"

        last_error = None
        for attempt in range(max_retries):
            status_code, body_bytes, latency_ms = self._request_fn(deployment_url, timeout=timeout)
            
            if 200 <= status_code < 400:
                body_text = body_bytes.decode("utf-8", errors="ignore")
                content_ok = True
                if expected_content and expected_content.lower() not in body_text.lower():
                    content_ok = False

                return HealthCheckResult(
                    target_url=deployment_url,
                    status_code=status_code,
                    is_healthy=content_ok,
                    latency_ms=round(latency_ms, 2),
                    content_verified=content_ok,
                    error_message=None if content_ok else f"Expected content '{expected_content}' missing in response body",
                    checked_at=datetime.utcnow().isoformat()
                )
            
            last_error = f"HTTP {status_code}: {body_bytes.decode('utf-8', errors='ignore')[:150]}"
            if attempt < max_retries - 1:
                time.sleep(2.0 * (attempt + 1))

        return HealthCheckResult(
            target_url=deployment_url,
            status_code=status_code if 'status_code' in locals() else None,
            is_healthy=False,
            latency_ms=round(latency_ms, 2) if 'latency_ms' in locals() else None,
            content_verified=False,
            error_message=last_error or "Health check connection failed",
            checked_at=datetime.utcnow().isoformat()
        )

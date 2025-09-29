import time
import logging
from fastapi import Request, Response
from typing import Callable

logger = logging.getLogger(__name__)


async def log_requests(request: Request, call_next: Callable) -> Response:
    """log requests"""
    start_time = time.time()

    # log request
    logger.info(f"Request: {request.method} {request.url.path}")

    try:
        response = await call_next(request)

        # calc time
        process_time = time.time() - start_time

        # log response
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Time: {process_time:.3f}s"
        )

        # add time header
        response.headers["X-Process-Time"] = str(process_time)

        return response

    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Error processing request: {request.method} {request.url.path} "
            f"- Error: {e} - Time: {process_time:.3f}s"
        )
        raise


async def add_security_headers(request: Request, call_next: Callable) -> Response:
    """add security headers"""
    response = await call_next(request)

    # add headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    return response

"""
Shared concurrency controls for background analysis tasks.
"""

import asyncio

# Limit concurrent analysis tasks to prevent resource exhaustion
# when multiple users run analyses simultaneously.
analysis_semaphore = asyncio.Semaphore(5)

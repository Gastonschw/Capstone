"""Run with isolated required configuration; never contacts authentication providers."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import httpx
from fastapi import HTTPException
from starlette.requests import Request

from dependencies import get_current_user_id
from services.user_service import require_registered_user


USER_ID = "d9428888-122b-11e1-b85c-61cd3cbb3210"


def request(headers):
    return Request({"type": "http", "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()]})


class AuthenticationTests(unittest.IsolatedAsyncioTestCase):
    async def test_forged_identity_header_is_not_authentication(self):
        with patch("dependencies.httpx.AsyncClient") as client:
            with self.assertRaises(HTTPException) as caught:
                await get_current_user_id(request({"X-User-Id": USER_ID}))
        self.assertEqual(caught.exception.status_code, 401)
        client.assert_not_called()

    async def test_verified_uuid_is_canonical_and_cached(self):
        client = AsyncMock()
        client.get.return_value = httpx.Response(200, json={"id": USER_ID.upper()})
        with patch("dependencies.httpx.AsyncClient") as factory:
            factory.return_value.__aenter__.return_value = client
            req = request({"Authorization": "Bearer test-token", "X-User-Id": str(UUID(int=1))})
            self.assertEqual(await get_current_user_id(req), USER_ID)
            self.assertEqual(await get_current_user_id(req), USER_ID)
        client.get.assert_awaited_once()
        self.assertEqual(client.get.call_args.kwargs["headers"]["Authorization"], "Bearer test-token")

    async def test_invalid_upstream_identity_fails_closed(self):
        for body in ({"id": "not-a-uuid"}, {"id": None}, [], {"id": 42}):
            with self.subTest(body=body):
                client = AsyncMock()
                client.get.return_value = httpx.Response(200, json=body)
                with patch("dependencies.httpx.AsyncClient") as factory:
                    factory.return_value.__aenter__.return_value = client
                    with self.assertRaises(HTTPException) as caught:
                        await get_current_user_id(request({"Authorization": "Bearer test-token"}))
                self.assertEqual(caught.exception.status_code, 401)
                self.assertNotIn("test-token", caught.exception.detail)

    async def test_provider_failure_does_not_expose_token(self):
        client = AsyncMock()
        client.get.side_effect = httpx.ConnectError("sensitive test-token")
        with patch("dependencies.httpx.AsyncClient") as factory:
            factory.return_value.__aenter__.return_value = client
            with self.assertRaises(HTTPException) as caught:
                await get_current_user_id(request({"Authorization": "Bearer test-token"}))
        self.assertEqual(caught.exception.status_code, 503)
        self.assertNotIn("test-token", caught.exception.detail)

    async def test_registration_requires_database_row(self):
        result = Mock()
        result.fetchone.return_value = None
        db = SimpleNamespace(execute=AsyncMock(return_value=result))
        with self.assertRaises(HTTPException) as caught:
            await require_registered_user(db, USER_ID)
        self.assertEqual(caught.exception.status_code, 400)
        result.fetchone.return_value = (UUID(USER_ID),)
        self.assertEqual(await require_registered_user(db, USER_ID), UUID(USER_ID))

    async def test_database_errors_are_not_swallowed(self):
        error = RuntimeError("transaction aborted")
        db = SimpleNamespace(execute=AsyncMock(side_effect=error))
        with self.assertRaises(RuntimeError) as caught:
            await require_registered_user(db, USER_ID)
        self.assertIs(caught.exception, error)

from __future__ import annotations

from uuid import UUID

import pytest
from django.http import HttpResponse, StreamingHttpResponse
from django.test import SimpleTestCase

from django_htmx.http import (
    HttpResponseClientRedirect,
    HttpResponseClientRefresh,
    HttpResponseStopPolling,
    trigger_client_event,
)


class HttpResponseStopPollingTests(SimpleTestCase):
    def test_success(self):
        response = HttpResponseStopPolling()

        assert response.status_code == 286
        assert response.reason_phrase == "Stop Polling"


class HttpResponseClientRedirectTests(SimpleTestCase):
    def test_success(self):
        response = HttpResponseClientRedirect("https://example.com")

        assert response.status_code == 200
        assert response["HX-Redirect"] == "https://example.com"
        assert "Location" not in response


class HttpResponseClientRefreshTests(SimpleTestCase):
    def test_success(self):
        response = HttpResponseClientRefresh()

        assert response.status_code == 200
        assert response["Content-Type"] == "text/html; charset=utf-8"
        assert response["HX-Refresh"] == "true"


class TriggerClientEventTests(SimpleTestCase):
    def test_fail_bad_after_value(self):
        response = HttpResponse()

        with pytest.raises(ValueError) as exinfo:
            trigger_client_event(
                response,
                "custom-event",
                {},
                after="bad-value",  # type: ignore [arg-type]
            )

        assert exinfo.value.args == (
            "Value for 'after' must be one of: 'receive', 'settle', or 'swap'.",
        )

    def test_fail_header_there_not_json(self):
        response = HttpResponse()
        response["HX-Trigger"] = "broken{"

        with pytest.raises(ValueError) as exinfo:
            trigger_client_event(response, "custom-event", {})

        assert exinfo.value.args == ("'HX-Trigger' value should be valid JSON.",)

    def test_success(self):
        response = HttpResponse()

        result = trigger_client_event(
            response, "showConfetti", {"colours": ["purple", "red"]}
        )

        assert result is response
        assert (
            response["HX-Trigger"] == '{"showConfetti": {"colours": ["purple", "red"]}}'
        )

    def test_success_streaming(self):
        response = StreamingHttpResponse(iter((b"hello",)))

        result = trigger_client_event(
            response, "showConfetti", {"colours": ["purple", "red"]}
        )

        assert result is response
        assert (
            response["HX-Trigger"] == '{"showConfetti": {"colours": ["purple", "red"]}}'
        )

    def test_success_multiple_events(self):
        response = HttpResponse()

        result1 = trigger_client_event(
            response, "showConfetti", {"colours": ["purple"]}
        )
        result2 = trigger_client_event(response, "showMessage", {"value": "Well done!"})

        assert result1 is response
        assert result2 is response
        assert response["HX-Trigger"] == (
            '{"showConfetti": {"colours": ["purple"]},'
            + ' "showMessage": {"value": "Well done!"}}'
        )

    def test_success_override(self):
        response = HttpResponse()

        trigger_client_event(response, "showMessage", {"value": "That was okay."})
        trigger_client_event(response, "showMessage", {"value": "Well done!"})

        assert response["HX-Trigger"] == '{"showMessage": {"value": "Well done!"}}'

    def test_success_after_settle(self):
        response = HttpResponse()

        trigger_client_event(
            response, "showMessage", {"value": "Great!"}, after="settle"
        )

        assert (
            response["HX-Trigger-After-Settle"]
            == '{"showMessage": {"value": "Great!"}}'
        )

    def test_success_after_swap(self):
        response = HttpResponse()

        trigger_client_event(response, "showMessage", {"value": "Great!"}, after="swap")

        assert (
            response["HX-Trigger-After-Swap"] == '{"showMessage": {"value": "Great!"}}'
        )

    def test_django_json_encoder(self):
        response = HttpResponse()
        uuid_value = UUID("{12345678-1234-5678-1234-567812345678}")

        trigger_client_event(response, "showMessage", {"uuid": uuid_value})

        assert (
            response["HX-Trigger"]
            == '{"showMessage": {"uuid": "12345678-1234-5678-1234-567812345678"}}'
        )

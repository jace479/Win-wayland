"""Policy-enforcing request dispatcher for the host bridge prototype."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .bridge_policy import authorize_operation
from .bridge_protocol import Message, ProtocolError, validate_application_request
from .bridge_session import BridgeSession
from .identity_policy import authorize_identity_request
from .app_catalog import ApplicationCatalog, ApplicationEntry


@dataclass(frozen=True)
class BrokerResult:
    operation: str
    payload: Mapping[str, Any]


class HostBroker:
    """Validate bridge requests before a platform adapter handles them."""

    def __init__(
        self,
        session: BridgeSession,
        application_allow_list: Mapping[str, str],
        identity_name: str = "Windows user",
        desktop_catalog: ApplicationCatalog | None = None,
    ) -> None:
        self.session = session
        self.application_allow_list = dict(application_allow_list)
        self.identity_name = identity_name
        self.desktop_catalog = desktop_catalog or ApplicationCatalog(
            tuple(
                ApplicationEntry(application_id, application_id, executable, origin="windows")
                for application_id, executable in self.application_allow_list.items()
            )
        )

    def dispatch(
        self, message: Message, privileged_capability: bool = False
    ) -> BrokerResult:
        if message.kind != "request":
            raise ProtocolError("host broker accepts request messages only")
        self.session.require_ready()
        authorize_operation(message.operation, privileged_capability)

        if message.operation == "app.launch":
            executable = validate_application_request(
                message.payload, self.application_allow_list
            )
            return BrokerResult(
                operation="app.launch.accepted",
                payload={"application": message.payload["application"], "executable": executable},
            )

        if message.operation == "app.list":
            return BrokerResult(
                operation="app.list.accepted",
                payload={"applications": self.desktop_catalog.list_for_desktop()},
            )

        if message.operation == "window.focus":
            window_id = message.payload.get("window")
            if not isinstance(window_id, str) or not window_id:
                raise ProtocolError("window.focus requires a window identifier")
            return BrokerResult("window.focus.accepted", {"window": window_id})

        if message.operation == "host.restart-bridge":
            return BrokerResult("host.restart-bridge.accepted", {})

        if message.operation in {"identity.session", "identity.sso-request"}:
            capability = (
                "session-identity"
                if message.operation == "identity.session"
                else "sso-request"
            )
            authorize_identity_request(capability, authenticated=True)
            payload = {"identity": self.identity_name}
            if message.operation == "identity.sso-request":
                payload["request"] = "approved-by-host"
            return BrokerResult(f"{message.operation}.accepted", payload)

        return BrokerResult(f"{message.operation}.accepted", {})
"""Config flow for Niko Home Control."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_TOKEN,
    DEFAULT_CLIENT_ID_PREFIX,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    DOMAIN,
)
from .niko_client import (
    NikoAuthenticationError,
    NikoCannotConnect,
    NikoClient,
    NikoError,
)

_LOGGER = logging.getLogger(__name__)


class NikoHomeControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for one Niko controller."""

    VERSION = 1
    MINOR_VERSION = 1

    async def _async_validate_connection(
        self,
        *,
        host: str,
        port: int,
        username: str,
        token: str,
    ) -> dict[str, str]:
        """Validate credentials against the controller."""

        errors: dict[str, str] = {}
        client = NikoClient(
            host=host,
            port=port,
            username=username,
            password=token,
            client_id=f"{DEFAULT_CLIENT_ID_PREFIX}-config-flow",
        )
        try:
            await client.async_start()
        except NikoAuthenticationError:
            errors["base"] = "invalid_auth"
        except NikoCannotConnect:
            errors["base"] = "cannot_connect"
        except NikoError:
            errors["base"] = "unknown"
        except Exception:  # pragma: no cover - HA boundary logging
            _LOGGER.exception("Unexpected exception validating Niko controller")
            errors["base"] = "unknown"
        finally:
            await client.async_stop()
        return errors

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            await self.async_set_unique_id(f"{host.lower()}:{port}")
            self._abort_if_unique_id_configured()

            errors = await self._async_validate_connection(
                host=host,
                port=port,
                username=user_input[CONF_USERNAME],
                token=user_input[CONF_TOKEN],
            )

            if not errors:
                return self.async_create_entry(
                    title=f"Niko Home Control II ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_TOKEN: user_input[CONF_TOKEN],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): TextSelector(),
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): TextSelector(
                    TextSelectorConfig(autocomplete="username")
                ),
                vol.Required(CONF_TOKEN): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.PASSWORD,
                        autocomplete="current-password",
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Replace the Hobby API credentials without removing the entry."""

        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            token = user_input[CONF_TOKEN]
            errors = await self._async_validate_connection(
                host=entry.data[CONF_HOST],
                port=entry.data[CONF_PORT],
                username=username,
                token=token,
            )
            if not errors:
                return self.async_update_and_abort(
                    entry,
                    data={
                        **entry.data,
                        CONF_USERNAME: username,
                        CONF_TOKEN: token,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME,
                    default=entry.data[CONF_USERNAME],
                ): TextSelector(TextSelectorConfig(autocomplete="username")),
                vol.Required(CONF_TOKEN): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.PASSWORD,
                        autocomplete="current-password",
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

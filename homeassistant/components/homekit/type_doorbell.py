"""Class to hold all doorbell accessories."""

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HassJobType,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util.async_ import create_eager_task

from .accessories import TYPES, HomeAccessory, Camera, HomeDriver
from .const import (
    CHAR_MOTION_DETECTED,
    CHAR_PROGRAMMABLE_SWITCH_EVENT,
    SERV_DOORBELL,
    SERV_MOTION_SENSOR,
    SERV_STATELESS_PROGRAMMABLE_SWITCH,
)
from .util import pid_is_alive, state_changed_event_is_same_state

_LOGGER = logging.getLogger(__name__)

DOORBELL_SINGLE_PRESS = 0
DOORBELL_DOUBLE_PRESS = 1
DOORBELL_LONG_PRESS = 2

@TYPES.register("Doorbell")
class Doorbell(HomeAccessory, Camera):  # type: ignore[misc]
    """Generate a Doorbell accessory."""

    def __init__(
        self,
        hass: HomeAssistant,
        driver: HomeDriver,
        name: str,
        entity_id: str,
        aid: int,
        config: dict[str, Any],
    ) -> None:
        """Initialize a stub Camera accessory object."""
        HomeAccessory.__init__(
            self,
            hass,
            driver,
            name,
            entity_id,
            aid,
            config,
            category=CATEGORY_CAMERA,
            options={},
        )

        self.linked_doorbell_sensor = entity_id
        self.doorbell_is_event = True

        serv_doorbell = self.add_preload_service(SERV_DOORBELL)
        self.set_primary_service(serv_doorbell)
        self._char_doorbell_detected = serv_doorbell.configure_char(
            CHAR_PROGRAMMABLE_SWITCH_EVENT,
            value=0,
        )
        serv_stateless_switch = self.add_preload_service(
            SERV_STATELESS_PROGRAMMABLE_SWITCH
        )
        self._char_doorbell_detected_switch = serv_stateless_switch.configure_char(
            CHAR_PROGRAMMABLE_SWITCH_EVENT,
            value=0,
            valid_values={"SinglePress": DOORBELL_SINGLE_PRESS},
        )
        serv_speaker = self.add_preload_service(SERV_SPEAKER)
        serv_speaker.configure_char(CHAR_MUTE, value=0)
        self._async_update_doorbell_state(None, state)

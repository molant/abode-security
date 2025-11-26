"""Tests for CMS Settings configuration switches."""

from unittest.mock import AsyncMock, patch

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .common import setup_platform
from .test_constants import (
    DISPATCH_FIRE_ENTITY_ID,
    DISPATCH_FIRE_UID,
    DISPATCH_MEDICAL_ENTITY_ID,
    DISPATCH_MEDICAL_UID,
    DISPATCH_POLICE_ENTITY_ID,
    DISPATCH_POLICE_UID,
    DISPATCH_WITHOUT_VERIFICATION_ENTITY_ID,
    DISPATCH_WITHOUT_VERIFICATION_UID,
    MONITORING_ACTIVE_ENTITY_ID,
    MONITORING_ACTIVE_UID,
    SEND_MEDIA_ENTITY_ID,
    SEND_MEDIA_UID,
)


# ============================================================================
# MONITORING_ACTIVE Tests
# ============================================================================


async def test_monitoring_active_entity_registry(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Test that monitoring_active is registered with correct unique_id."""
    await setup_platform(hass, SWITCH_DOMAIN)

    entry = entity_registry.async_get(MONITORING_ACTIVE_ENTITY_ID)
    assert entry is not None
    assert entry.unique_id == MONITORING_ACTIVE_UID


async def test_monitoring_active_attributes(hass: HomeAssistant) -> None:
    """Test the monitoring_active switch attributes are correct."""
    await setup_platform(hass, SWITCH_DOMAIN)

    state = hass.states.get(MONITORING_ACTIVE_ENTITY_ID)
    assert state is not None


async def test_monitoring_active_initial_status_on(hass: HomeAssistant) -> None:
    """Test that monitoring_active switch pulls initial status when enabled."""
    with patch(
        "custom_components.abode_security.models.AbodeSystem.get_monitoring_active",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = True
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(MONITORING_ACTIVE_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_ON


async def test_monitoring_active_initial_status_off(hass: HomeAssistant) -> None:
    """Test that monitoring_active switch pulls initial status when disabled."""
    with patch(
        "custom_components.abode_security.models.AbodeSystem.get_monitoring_active",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = False
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(MONITORING_ACTIVE_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_OFF


async def test_monitoring_active_turn_on(hass: HomeAssistant) -> None:
    """Test the monitoring_active switch can be turned on."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_monitoring_active",
        new_callable=AsyncMock,
    ) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: MONITORING_ACTIVE_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(True)


async def test_monitoring_active_turn_off(hass: HomeAssistant) -> None:
    """Test the monitoring_active switch can be turned off."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_monitoring_active",
        new_callable=AsyncMock,
    ) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: MONITORING_ACTIVE_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(False)


async def test_monitoring_active_error_handling(hass: HomeAssistant) -> None:
    """Test that monitoring_active handles errors gracefully."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_monitoring_active",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = Exception("API Error")
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: MONITORING_ACTIVE_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Entity should still exist despite error
        state = hass.states.get(MONITORING_ACTIVE_ENTITY_ID)
        assert state is not None


# ============================================================================
# SEND_MEDIA Tests
# ============================================================================


async def test_send_media_entity_registry(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Test that send_media is registered with correct unique_id."""
    await setup_platform(hass, SWITCH_DOMAIN)

    entry = entity_registry.async_get(SEND_MEDIA_ENTITY_ID)
    assert entry is not None
    assert entry.unique_id == SEND_MEDIA_UID


async def test_send_media_attributes(hass: HomeAssistant) -> None:
    """Test the send_media switch attributes are correct."""
    await setup_platform(hass, SWITCH_DOMAIN)

    state = hass.states.get(SEND_MEDIA_ENTITY_ID)
    assert state is not None


async def test_send_media_initial_status_on(hass: HomeAssistant) -> None:
    """Test that send_media switch pulls initial status when enabled."""
    with patch(
        "custom_components.abode_security.models.AbodeSystem.get_send_media",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = True
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(SEND_MEDIA_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_ON


async def test_send_media_initial_status_off(hass: HomeAssistant) -> None:
    """Test that send_media switch pulls initial status when disabled."""
    with patch(
        "custom_components.abode_security.models.AbodeSystem.get_send_media",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = False
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(SEND_MEDIA_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_OFF


async def test_send_media_turn_on(hass: HomeAssistant) -> None:
    """Test the send_media switch can be turned on."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_send_media",
        new_callable=AsyncMock,
    ) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: SEND_MEDIA_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(True)


async def test_send_media_turn_off(hass: HomeAssistant) -> None:
    """Test the send_media switch can be turned off."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_send_media",
        new_callable=AsyncMock,
    ) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: SEND_MEDIA_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(False)


async def test_send_media_error_handling(hass: HomeAssistant) -> None:
    """Test that send_media handles errors gracefully."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_send_media",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = Exception("API Error")
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: SEND_MEDIA_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Entity should still exist despite error
        state = hass.states.get(SEND_MEDIA_ENTITY_ID)
        assert state is not None


# ============================================================================
# DISPATCH_WITHOUT_VERIFICATION Tests
# ============================================================================


async def test_dispatch_without_verification_entity_registry(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Test that dispatch_without_verification is registered with correct unique_id."""
    await setup_platform(hass, SWITCH_DOMAIN)

    entry = entity_registry.async_get(DISPATCH_WITHOUT_VERIFICATION_ENTITY_ID)
    assert entry is not None
    assert entry.unique_id == DISPATCH_WITHOUT_VERIFICATION_UID


async def test_dispatch_without_verification_attributes(hass: HomeAssistant) -> None:
    """Test the dispatch_without_verification switch attributes are correct."""
    await setup_platform(hass, SWITCH_DOMAIN)

    state = hass.states.get(DISPATCH_WITHOUT_VERIFICATION_ENTITY_ID)
    assert state is not None


async def test_dispatch_without_verification_initial_status_on(
    hass: HomeAssistant,
) -> None:
    """Test that dispatch_without_verification switch pulls initial status when enabled."""
    with patch(
        "custom_components.abode_security.models.AbodeSystem.get_dispatch_without_verification",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = True
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(DISPATCH_WITHOUT_VERIFICATION_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_ON


async def test_dispatch_without_verification_initial_status_off(
    hass: HomeAssistant,
) -> None:
    """Test that dispatch_without_verification switch pulls initial status when disabled."""
    with patch(
        "custom_components.abode_security.models.AbodeSystem.get_dispatch_without_verification",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = False
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(DISPATCH_WITHOUT_VERIFICATION_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_OFF


async def test_dispatch_without_verification_turn_on(hass: HomeAssistant) -> None:
    """Test the dispatch_without_verification switch can be turned on."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_dispatch_without_verification",
        new_callable=AsyncMock,
    ) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: DISPATCH_WITHOUT_VERIFICATION_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(True)


async def test_dispatch_without_verification_turn_off(hass: HomeAssistant) -> None:
    """Test the dispatch_without_verification switch can be turned off."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_dispatch_without_verification",
        new_callable=AsyncMock,
    ) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: DISPATCH_WITHOUT_VERIFICATION_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(False)


async def test_dispatch_without_verification_error_handling(
    hass: HomeAssistant,
) -> None:
    """Test that dispatch_without_verification handles errors gracefully."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_dispatch_without_verification",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = Exception("API Error")
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: DISPATCH_WITHOUT_VERIFICATION_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Entity should still exist despite error
        state = hass.states.get(DISPATCH_WITHOUT_VERIFICATION_ENTITY_ID)
        assert state is not None


# ============================================================================
# DISPATCH_POLICE Tests
# ============================================================================


async def test_dispatch_police_entity_registry(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Test that dispatch_police is registered with correct unique_id."""
    await setup_platform(hass, SWITCH_DOMAIN)

    entry = entity_registry.async_get(DISPATCH_POLICE_ENTITY_ID)
    assert entry is not None
    assert entry.unique_id == DISPATCH_POLICE_UID


async def test_dispatch_police_attributes(hass: HomeAssistant) -> None:
    """Test the dispatch_police switch attributes are correct."""
    await setup_platform(hass, SWITCH_DOMAIN)

    state = hass.states.get(DISPATCH_POLICE_ENTITY_ID)
    assert state is not None


async def test_dispatch_police_initial_status_on(hass: HomeAssistant) -> None:
    """Test that dispatch_police switch pulls initial status when enabled."""
    with patch(
        "custom_components.abode_security.models.AbodeSystem.get_dispatch_police",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = True
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(DISPATCH_POLICE_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_ON


async def test_dispatch_police_initial_status_off(hass: HomeAssistant) -> None:
    """Test that dispatch_police switch pulls initial status when disabled."""
    with patch(
        "custom_components.abode_security.models.AbodeSystem.get_dispatch_police",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = False
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(DISPATCH_POLICE_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_OFF


async def test_dispatch_police_turn_on(hass: HomeAssistant) -> None:
    """Test the dispatch_police switch can be turned on."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_dispatch_police",
        new_callable=AsyncMock,
    ) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: DISPATCH_POLICE_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(True)


async def test_dispatch_police_turn_off(hass: HomeAssistant) -> None:
    """Test the dispatch_police switch can be turned off."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_dispatch_police",
        new_callable=AsyncMock,
    ) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: DISPATCH_POLICE_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(False)


async def test_dispatch_police_error_handling(hass: HomeAssistant) -> None:
    """Test that dispatch_police handles errors gracefully."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_dispatch_police",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = Exception("API Error")
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: DISPATCH_POLICE_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Entity should still exist despite error
        state = hass.states.get(DISPATCH_POLICE_ENTITY_ID)
        assert state is not None


# ============================================================================
# DISPATCH_FIRE Tests
# ============================================================================


async def test_dispatch_fire_entity_registry(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Test that dispatch_fire is registered with correct unique_id."""
    await setup_platform(hass, SWITCH_DOMAIN)

    entry = entity_registry.async_get(DISPATCH_FIRE_ENTITY_ID)
    assert entry is not None
    assert entry.unique_id == DISPATCH_FIRE_UID


async def test_dispatch_fire_attributes(hass: HomeAssistant) -> None:
    """Test the dispatch_fire switch attributes are correct."""
    await setup_platform(hass, SWITCH_DOMAIN)

    state = hass.states.get(DISPATCH_FIRE_ENTITY_ID)
    assert state is not None


async def test_dispatch_fire_initial_status_on(hass: HomeAssistant) -> None:
    """Test that dispatch_fire switch pulls initial status when enabled."""
    with patch(
        "custom_components.abode_security.models.AbodeSystem.get_dispatch_fire",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = True
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(DISPATCH_FIRE_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_ON


async def test_dispatch_fire_initial_status_off(hass: HomeAssistant) -> None:
    """Test that dispatch_fire switch pulls initial status when disabled."""
    with patch(
        "custom_components.abode_security.models.AbodeSystem.get_dispatch_fire",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = False
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(DISPATCH_FIRE_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_OFF


async def test_dispatch_fire_turn_on(hass: HomeAssistant) -> None:
    """Test the dispatch_fire switch can be turned on."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_dispatch_fire",
        new_callable=AsyncMock,
    ) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: DISPATCH_FIRE_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(True)


async def test_dispatch_fire_turn_off(hass: HomeAssistant) -> None:
    """Test the dispatch_fire switch can be turned off."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_dispatch_fire",
        new_callable=AsyncMock,
    ) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: DISPATCH_FIRE_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(False)


async def test_dispatch_fire_error_handling(hass: HomeAssistant) -> None:
    """Test that dispatch_fire handles errors gracefully."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_dispatch_fire",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = Exception("API Error")
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: DISPATCH_FIRE_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Entity should still exist despite error
        state = hass.states.get(DISPATCH_FIRE_ENTITY_ID)
        assert state is not None


# ============================================================================
# DISPATCH_MEDICAL Tests
# ============================================================================


async def test_dispatch_medical_entity_registry(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Test that dispatch_medical is registered with correct unique_id."""
    await setup_platform(hass, SWITCH_DOMAIN)

    entry = entity_registry.async_get(DISPATCH_MEDICAL_ENTITY_ID)
    assert entry is not None
    assert entry.unique_id == DISPATCH_MEDICAL_UID


async def test_dispatch_medical_attributes(hass: HomeAssistant) -> None:
    """Test the dispatch_medical switch attributes are correct."""
    await setup_platform(hass, SWITCH_DOMAIN)

    state = hass.states.get(DISPATCH_MEDICAL_ENTITY_ID)
    assert state is not None


async def test_dispatch_medical_initial_status_on(hass: HomeAssistant) -> None:
    """Test that dispatch_medical switch pulls initial status when enabled."""
    with patch(
        "custom_components.abode_security.models.AbodeSystem.get_dispatch_medical",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = True
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(DISPATCH_MEDICAL_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_ON


async def test_dispatch_medical_initial_status_off(hass: HomeAssistant) -> None:
    """Test that dispatch_medical switch pulls initial status when disabled."""
    with patch(
        "custom_components.abode_security.models.AbodeSystem.get_dispatch_medical",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = False
        await setup_platform(hass, SWITCH_DOMAIN)
        await hass.async_block_till_done()

        state = hass.states.get(DISPATCH_MEDICAL_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_OFF


async def test_dispatch_medical_turn_on(hass: HomeAssistant) -> None:
    """Test the dispatch_medical switch can be turned on."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_dispatch_medical",
        new_callable=AsyncMock,
    ) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: DISPATCH_MEDICAL_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(True)


async def test_dispatch_medical_turn_off(hass: HomeAssistant) -> None:
    """Test the dispatch_medical switch can be turned off."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_dispatch_medical",
        new_callable=AsyncMock,
    ) as mock:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: DISPATCH_MEDICAL_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock.assert_called_once_with(False)


async def test_dispatch_medical_error_handling(hass: HomeAssistant) -> None:
    """Test that dispatch_medical handles errors gracefully."""
    await setup_platform(hass, SWITCH_DOMAIN)

    with patch(
        "custom_components.abode_security.models.AbodeSystem.set_dispatch_medical",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = Exception("API Error")
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: DISPATCH_MEDICAL_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Entity should still exist despite error
        state = hass.states.get(DISPATCH_MEDICAL_ENTITY_ID)
        assert state is not None

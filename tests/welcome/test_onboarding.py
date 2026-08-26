from types import SimpleNamespace
from unittest.mock import AsyncMock
import unittest

import discord

from cody.config import (
    PARTICIPANT_ROLE_ID,
    ROLE_CHANNEL_ID,
    ROLE_WELCOME_IMAGE,
    SPONSOR_REVIEW_CHANNEL_ID,
    SPONSOR_ROLE_ID,
    SPONSOR_UNDER_REVIEW_ROLE_ID,
    VISITOR_ROLE_ID,
)
from cody.features.welcome.cog import OnboardingCog
from cody.features.welcome.models import SponsorDecision
from cody.features.welcome.providers import (
    BackendParticipantLinkProvider,
    ParticipantNotLinked,
    participant_link_from_data,
)
from cody.features.welcome.service import replace_access_role
from cody.features.welcome.views import (
    ROLE_PANEL_MARKER,
    RoleSelectionView,
    SponsorReviewView,
    pending_sponsor_marker,
    resolved_sponsor_review_embed,
    role_panel_embed,
    sponsor_applicant_id,
    sponsor_review_embed,
    website_signup_view,
)
from cody.integrations.backend.actions import BackendAction
from cody.integrations.backend.errors import BackendActionError
from cody.integrations.backend.models import BackendResult


class OnboardingConfigurationTests(unittest.TestCase):
    def test_supplied_channel_and_role_defaults_are_configured(self) -> None:
        self.assertEqual(ROLE_CHANNEL_ID, 1542168230896996352)
        self.assertEqual(SPONSOR_REVIEW_CHANNEL_ID, 1542176692791939232)
        self.assertEqual(PARTICIPANT_ROLE_ID, 1541112817476702238)
        self.assertEqual(SPONSOR_ROLE_ID, 1542162836791361576)
        self.assertEqual(SPONSOR_UNDER_REVIEW_ROLE_ID, 1542164526022004877)
        self.assertEqual(VISITOR_ROLE_ID, 1542164969796272229)
        self.assertTrue(ROLE_WELCOME_IMAGE.is_file())

    def test_admin_commands_have_role_checks_and_visibility(self) -> None:
        command_checks = {
            command.name: [check.__name__ for check in command.checks]
            for command in OnboardingCog.__cog_app_commands__
        }
        permissions = getattr(
            OnboardingCog,
            "__discord_app_commands_default_permissions__",
        )

        self.assertEqual(
            command_checks,
            {
                "setup": ["admin_access_check"],
                "status": ["admin_access_check"],
            },
        )
        self.assertEqual(permissions, discord.Permissions(administrator=True))


class OnboardingViewTests(unittest.IsolatedAsyncioTestCase):
    async def test_role_and_review_controls_are_persistent(self) -> None:
        controller = SimpleNamespace()
        role_view = RoleSelectionView(controller)
        review_view = SponsorReviewView(controller)

        self.assertTrue(role_view.is_persistent())
        self.assertTrue(review_view.is_persistent())
        self.assertEqual(
            [item.custom_id for item in role_view.children],
            [
                "cody:onboarding:participant",
                "cody:onboarding:sponsor",
                "cody:onboarding:visitor",
            ],
        )
        self.assertEqual(
            [item.custom_id for item in review_view.children],
            [
                "cody:onboarding:sponsor:approve",
                "cody:onboarding:sponsor:reject",
            ],
        )

    def test_role_panel_uses_supplied_artwork_and_marker(self) -> None:
        embed = role_panel_embed(ROLE_WELCOME_IMAGE.name)

        self.assertEqual(embed.footer.text, ROLE_PANEL_MARKER)
        self.assertEqual(
            embed.image.url,
            f"attachment://{ROLE_WELCOME_IMAGE.name}",
        )

    def test_review_marker_recovers_applicant_and_changes_when_resolved(self) -> None:
        member = SimpleNamespace(id=123456789012345678, mention="<@123456789012345678>")
        pending = sponsor_review_embed(member)
        message = SimpleNamespace(embeds=[pending])

        self.assertEqual(
            pending.footer.text,
            pending_sponsor_marker(member.id),
        )
        self.assertEqual(sponsor_applicant_id(message), member.id)

        resolved = resolved_sponsor_review_embed(
            pending,
            applicant_id=member.id,
            reviewer_id=987654321098765432,
            decision=SponsorDecision.APPROVED,
        )
        self.assertEqual(sponsor_applicant_id(SimpleNamespace(embeds=[resolved])), None)
        self.assertIn("APPROVED", resolved.footer.text)

    def test_signup_button_requires_safe_https_url(self) -> None:
        self.assertIsNotNone(website_signup_view("https://battlecode.example/signup"))
        self.assertIsNone(website_signup_view("http://battlecode.example/signup"))
        self.assertIsNone(website_signup_view("https://user:secret@example.com"))


class ParticipantProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_backend_provider_attests_the_discord_actor(self) -> None:
        client = SimpleNamespace(
            call=AsyncMock(
                return_value=BackendResult(
                    request_id="883eab63-4170-4ed7-a1b4-95c4fc477421",
                    data={
                        "participant_id": "participant-42",
                        "display_name": "Alice",
                        "team_id": None,
                    },
                    server_time="2026-08-26T12:00:00Z",
                )
            )
        )
        provider = BackendParticipantLinkProvider(client)

        link = await provider.get_link(
            discord_user_id=123,
            discord_guild_id=456,
            discord_interaction_id=789,
        )

        self.assertEqual(link.participant_id, "participant-42")
        client.call.assert_awaited_once_with(
            BackendAction.PARTICIPANT_GET,
            actor_discord_user_id=123,
            discord_guild_id=456,
            discord_interaction_id=789,
            payload={},
        )

    async def test_unlinked_backend_response_is_a_distinct_safe_outcome(self) -> None:
        client = SimpleNamespace(
            call=AsyncMock(
                side_effect=BackendActionError(
                    code="USER_NOT_LINKED",
                    request_id="883eab63-4170-4ed7-a1b4-95c4fc477421",
                    retryable=False,
                    http_status=404,
                )
            )
        )
        provider = BackendParticipantLinkProvider(client)

        with self.assertRaises(ParticipantNotLinked):
            await provider.get_link(
                discord_user_id=123,
                discord_guild_id=456,
                discord_interaction_id=789,
            )

    def test_participant_response_translation_is_strict(self) -> None:
        with self.assertRaises(ValueError):
            participant_link_from_data(
                {"participant_id": "participant-42", "display_name": ""}
            )
        with self.assertRaises(ValueError):
            participant_link_from_data(
                {"participant_id": "x" * 129, "display_name": "Alice"}
            )


class AccessRoleServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_replaces_only_cody_access_roles(self) -> None:
        default_role = SimpleNamespace(id=1)
        unrelated_role = SimpleNamespace(id=55)
        participant_role = SimpleNamespace(id=PARTICIPANT_ROLE_ID)
        visitor_role = SimpleNamespace(id=VISITOR_ROLE_ID)
        roles = {
            VISITOR_ROLE_ID: visitor_role,
        }
        guild = SimpleNamespace(id=1, get_role=roles.get)
        member = SimpleNamespace(
            guild=guild,
            roles=[default_role, unrelated_role, participant_role],
            edit=AsyncMock(),
        )

        assigned = await replace_access_role(
            member,
            VISITOR_ROLE_ID,
            reason="test",
        )

        self.assertIs(assigned, visitor_role)
        member.edit.assert_awaited_once_with(
            roles=[unrelated_role, visitor_role],
            reason="test",
        )


if __name__ == "__main__":
    unittest.main()

"""Welcome delivery, access selection, and sponsor-review Discord controls."""

from __future__ import annotations

import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from cody.config import (
    ADMIN_ROLE_ID,
    ORGANIZER_ROLE_ID,
    PARTICIPANT_ROLE_ID,
    ROLE_CHANNEL_ID,
    ROLE_WELCOME_IMAGE,
    RULES_IMAGE,
    RULES_CHANNEL_ID,
    STATS_MEMBERS_CHANNEL_ID,
    SPONSOR_REVIEW_CHANNEL_ID,
    SPONSOR_ROLE_ID,
    SPONSOR_UNDER_REVIEW_ROLE_ID,
    VISITOR_ROLE_ID,
    WELCOME_CHANNEL_ID,
    get_website_signup_url,
)
from cody.features.welcome.models import SponsorDecision
from cody.features.welcome.providers import (
    BackendParticipantLinkProvider,
    ParticipantLinkProvider,
    ParticipantNotLinked,
    ParticipantVerificationUnavailable,
)
from cody.features.welcome.rules import ServerRulesError, load_server_rules
from cody.features.welcome.service import (
    OnboardingSetupError,
    accept_server_rules,
    ensure_rules_accepted_role,
    find_rules_accepted_role,
    remove_access_roles,
    replace_access_role,
    send_welcome_message,
)
from cody.features.welcome.views import (
    ROLE_PANEL_MARKER,
    RULES_PANEL_PREFIX,
    RoleSelectionView,
    RulesAcceptanceView,
    SponsorReviewView,
    pending_sponsor_marker,
    resolved_sponsor_review_embed,
    role_channel_link_view,
    role_panel_embed,
    rules_channel_link_view,
    rules_panel_embed,
    sponsor_applicant_id,
    sponsor_review_embed,
    website_signup_view,
)
from cody.integrations.backend.errors import (
    BackendConfigurationError,
    BackendIntegrationError,
)
from cody.shared.colors import CodyColor
from cody.shared.components import cody_embed
from cody.shared.permissions import admin_only, is_sponsor_reviewer


LOGGER = logging.getLogger(__name__)


class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        await send_welcome_message(member)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if channel is None:
            LOGGER.error("Welcome channel %s was not found", WELCOME_CHANNEL_ID)
            return

        bot_member = channel.guild.me
        if bot_member is None:
            LOGGER.error("Cody's guild member could not be resolved")
            return

        permissions = channel.permissions_for(bot_member)
        LOGGER.info(
            "Welcome permissions | view=%s send=%s embeds=%s files=%s history=%s",
            permissions.view_channel,
            permissions.send_messages,
            permissions.embed_links,
            permissions.attach_files,
            permissions.read_message_history,
        )

    @app_commands.command(
        name="test_welcome",
        description="Test Cody's welcome message in the configured welcome channel.",
    )
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def test_welcome(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "This command can only be used inside a server.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        sent = await send_welcome_message(interaction.user)

        if sent:
            result = f"Welcome test sent to <#{WELCOME_CHANNEL_ID}>."
        else:
            result = f"Welcome channel <#{WELCOME_CHANNEL_ID}> was not found."

        await interaction.edit_original_response(content=result)


@app_commands.default_permissions(administrator=True)
class OnboardingCog(
    commands.GroupCog,
    group_name="onboarding",
    group_description="Configure and inspect Cody's access onboarding.",
):
    def __init__(
        self,
        bot: commands.Bot,
        participant_provider: ParticipantLinkProvider | None = None,
    ) -> None:
        self.bot = bot
        self._ready_initialised = False
        self._review_locks: dict[int, asyncio.Lock] = {}
        self._backend_configuration_error: str | None = None

        if participant_provider is None:
            try:
                participant_provider = BackendParticipantLinkProvider.from_environment()
            except BackendConfigurationError as error:
                self._backend_configuration_error = str(error)
        self.participant_provider = participant_provider

        # Fixed custom IDs and no timeouts keep both workflows usable after restart.
        self.bot.add_view(RulesAcceptanceView(self))
        self.bot.add_view(RoleSelectionView(self))
        self.bot.add_view(SponsorReviewView(self))

    async def cog_unload(self) -> None:
        if isinstance(self.participant_provider, BackendParticipantLinkProvider):
            await self.participant_provider.close()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self._ready_initialised:
            return
        channel = self._role_channel()
        rules_channel = self._rules_channel()
        if channel is None:
            LOGGER.error(
                "Role-selection channel %s was not found or is not visible",
                ROLE_CHANNEL_ID,
            )
            return
        if rules_channel is None or rules_channel.guild.id != channel.guild.id:
            LOGGER.error(
                "Rules channel %s was not found or is not visible",
                RULES_CHANNEL_ID,
            )
            return
        try:
            await ensure_rules_accepted_role(channel.guild)
            await self.ensure_rules_panel(rules_channel)
            await self.ensure_role_panel(channel)
        except (OnboardingSetupError, discord.Forbidden, discord.HTTPException):
            LOGGER.exception("Could not initialise Cody's role-selection panel")
            return

        self._ready_initialised = True
        if self.participant_provider is None:
            LOGGER.warning(
                "Participant access checks are disabled: %s",
                self._backend_configuration_error or "backend not configured",
            )
        LOGGER.info(
            "Access onboarding online | rules_channel=%s role_channel=%s "
            "sponsor_review=%s",
            RULES_CHANNEL_ID,
            ROLE_CHANNEL_ID,
            SPONSOR_REVIEW_CHANNEL_ID,
        )

    async def accept_rules(self, interaction: discord.Interaction) -> None:
        if (
            interaction.channel_id != RULES_CHANNEL_ID
            or interaction.guild is None
            or not isinstance(interaction.user, discord.Member)
        ):
            await interaction.response.send_message(
                "Rules can only be accepted in Cody's configured Rules channel.",
                ephemeral=True,
            )
            return

        try:
            current_rules = load_server_rules()
        except ServerRulesError as error:
            LOGGER.error("Rules acceptance content failed validation: %s", error)
            await interaction.response.send_message(
                "Cody's server-rule content needs Admin attention.",
                ephemeral=True,
            )
            return
        expected_marker = f"{RULES_PANEL_PREFIX} {current_rules.version}"
        if (
            interaction.message is None
            or self.bot.user is None
            or interaction.message.author.id != self.bot.user.id
            or not any(
                embed.footer.text == expected_marker
                for embed in interaction.message.embeds
                if embed.footer is not None
            )
        ):
            await interaction.response.send_message(
                "This rules panel is outdated. Ask an Admin to run "
                "`/onboarding setup`, then accept the current rules.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            role = await accept_server_rules(interaction.user)
        except OnboardingSetupError as error:
            LOGGER.error("Rules acceptance setup failed: %s", error)
            await interaction.edit_original_response(
                content="Cody's Rules Accepted role setup needs Admin attention."
            )
            return
        except (discord.Forbidden, discord.HTTPException):
            LOGGER.exception("Discord rejected Rules Accepted role assignment")
            await interaction.edit_original_response(
                content=(
                    "Cody could not record your acceptance. An Admin should check "
                    "Manage Roles permission and Cody's role position."
                )
            )
            return

        LOGGER.info(
            "Server rules accepted | member=%s role=%s",
            interaction.user.id,
            role.id,
        )
        await interaction.edit_original_response(
            content=(
                "Rules accepted. This acknowledgement does not unlock server "
                "areas by itself; choose your access role to continue."
            ),
            view=role_channel_link_view(interaction.guild.id),
        )

    async def select_participant(self, interaction: discord.Interaction) -> None:
        member = await self._role_selection_member(interaction)
        if member is None:
            return
        if self.participant_provider is None:
            await interaction.response.send_message(
                "Participant verification is not configured yet. Please ask an "
                "organiser to check `/onboarding status`.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self.participant_provider.get_link(
                discord_user_id=member.id,
                discord_guild_id=member.guild.id,
                discord_interaction_id=interaction.id,
            )
        except ParticipantNotLinked:
            link_view = website_signup_view(get_website_signup_url())
            suffix = (
                ""
                if link_view is not None
                else " Ask an organiser for the official registration link."
            )
            await interaction.edit_original_response(
                content=(
                    "Your Discord account is not linked to an ETH Battlecode "
                    "participant yet. Sign in or register on the official website "
                    f"with Discord, then press Participant again.{suffix}"
                ),
                view=link_view,
            )
            return
        except (ParticipantVerificationUnavailable, BackendIntegrationError) as error:
            request_id = getattr(error, "request_id", None)
            reference = f" Reference: `{request_id}`." if request_id else ""
            LOGGER.warning(
                "Participant linkage check failed | member=%s request_id=%s",
                member.id,
                request_id or "unavailable",
            )
            await interaction.edit_original_response(
                content=(
                    "Cody could not verify your website account right now. "
                    f"Please try again shortly.{reference}"
                )
            )
            return

        try:
            await replace_access_role(
                member,
                PARTICIPANT_ROLE_ID,
                reason="Cody participant linkage verified by the Main Backend",
            )
        except OnboardingSetupError as error:
            LOGGER.error("Participant role setup failed: %s", error)
            await interaction.edit_original_response(
                content="Cody's Participant role setup needs Admin attention."
            )
            return
        except (discord.Forbidden, discord.HTTPException):
            LOGGER.exception("Discord rejected Participant role assignment")
            await interaction.edit_original_response(
                content=(
                    "Your account is linked, but Cody could not assign the "
                    "Participant role. An Admin should check role hierarchy and "
                    "Manage Roles permission."
                )
            )
            return

        LOGGER.info("Participant access assigned | member=%s", member.id)
        await interaction.edit_original_response(
            content="Website link verified. Your **Participant** access is active."
        )

    async def select_sponsor(self, interaction: discord.Interaction) -> None:
        member = await self._role_selection_member(interaction)
        if member is None:
            return
        if self._member_has_role(member, SPONSOR_ROLE_ID):
            await interaction.response.send_message(
                "Your Sponsor access is already approved.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await replace_access_role(
                member,
                SPONSOR_UNDER_REVIEW_ROLE_ID,
                reason="Cody sponsor access requested",
            )
        except OnboardingSetupError as error:
            LOGGER.error("Sponsor role setup failed: %s", error)
            await interaction.edit_original_response(
                content="Cody's Sponsor role setup needs Admin attention."
            )
            return
        except (discord.Forbidden, discord.HTTPException):
            LOGGER.exception("Discord rejected Under Review role assignment")
            await interaction.edit_original_response(
                content=(
                    "Cody could not assign the Under Review role. An Admin should "
                    "check role hierarchy and Manage Roles permission."
                )
            )
            return

        try:
            review = await self.ensure_sponsor_review(member)
        except (OnboardingSetupError, discord.Forbidden, discord.HTTPException):
            LOGGER.exception(
                "Under Review assigned but sponsor review could not be posted | member=%s",
                member.id,
            )
            await interaction.edit_original_response(
                content=(
                    "Your **Under Review** access is active, but Cody could not "
                    "notify the organisers. Please contact an Admin; pressing "
                    "Sponsor again will safely retry the review notice."
                )
            )
            return

        LOGGER.info(
            "Sponsor access requested | member=%s review_message=%s",
            member.id,
            review.id,
        )
        await interaction.edit_original_response(
            content=(
                "Your **Under Review** access is active. An Admin or Organiser "
                "will review the Sponsor request."
            )
        )

    async def select_visitor(self, interaction: discord.Interaction) -> None:
        member = await self._role_selection_member(interaction)
        if member is None:
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await replace_access_role(
                member,
                VISITOR_ROLE_ID,
                reason="Cody visitor access selected",
            )
        except OnboardingSetupError as error:
            LOGGER.error("Visitor role setup failed: %s", error)
            await interaction.edit_original_response(
                content="Cody's Visitor role setup needs Admin attention."
            )
            return
        except (discord.Forbidden, discord.HTTPException):
            LOGGER.exception("Discord rejected Visitor role assignment")
            await interaction.edit_original_response(
                content=(
                    "Cody could not assign the Visitor role. An Admin should check "
                    "role hierarchy and Manage Roles permission."
                )
            )
            return

        await self._withdraw_pending_review(member)
        LOGGER.info("Visitor access assigned | member=%s", member.id)
        await interaction.edit_original_response(
            content="Your **Visitor** access is active. Welcome to ETH Battlecode."
        )

    async def review_sponsor(
        self,
        interaction: discord.Interaction,
        decision: SponsorDecision,
    ) -> None:
        if (
            interaction.channel_id != SPONSOR_REVIEW_CHANNEL_ID
            or interaction.guild is None
            or not isinstance(interaction.user, discord.Member)
        ):
            await interaction.response.send_message(
                "Sponsor review controls only work in Cody's configured review channel.",
                ephemeral=True,
            )
            return
        if not is_sponsor_reviewer(interaction.user):
            await interaction.response.send_message(
                "Only the configured Admin or Organiser role can review sponsors.",
                ephemeral=True,
            )
            return

        applicant_id = sponsor_applicant_id(interaction.message)
        if applicant_id is None:
            await interaction.response.send_message(
                "This sponsor review card is missing Cody's pending marker.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        lock = self._review_locks.setdefault(applicant_id, asyncio.Lock())
        async with lock:
            applicant = await self._resolve_member(interaction.guild, applicant_id)
            if applicant is None:
                await interaction.edit_original_response(
                    content="That applicant is no longer a member of this server."
                )
                return

            try:
                accepted_role = find_rules_accepted_role(interaction.guild)
            except OnboardingSetupError as error:
                LOGGER.error("Sponsor review rules gate failed: %s", error)
                await interaction.edit_original_response(
                    content="Cody's Rules Accepted role setup needs Admin attention."
                )
                return
            if accepted_role is None or not self._member_has_role(
                applicant,
                accepted_role.id,
            ):
                await interaction.edit_original_response(
                    content=(
                        "The applicant must accept the server rules before this "
                        "Sponsor request can be resolved. No role was changed."
                    )
                )
                return

            has_sponsor = self._member_has_role(applicant, SPONSOR_ROLE_ID)
            is_pending = self._member_has_role(
                applicant,
                SPONSOR_UNDER_REVIEW_ROLE_ID,
            )
            if has_sponsor:
                await interaction.edit_original_response(
                    content="That applicant already has approved Sponsor access."
                )
                return
            if not is_pending:
                await interaction.edit_original_response(
                    content=(
                        "That applicant no longer has an active Sponsor request; "
                        "no role was changed."
                    )
                )
                return

            target_role_id = (
                SPONSOR_ROLE_ID
                if decision is SponsorDecision.APPROVED
                else VISITOR_ROLE_ID
            )
            try:
                await replace_access_role(
                    applicant,
                    target_role_id,
                    reason=(
                        f"Cody sponsor request {decision.value} by "
                        f"Discord staff member {interaction.user.id}"
                    ),
                )
            except OnboardingSetupError as error:
                LOGGER.error("Sponsor decision role setup failed: %s", error)
                await interaction.edit_original_response(
                    content="Cody's Sponsor role setup needs Admin attention."
                )
                return
            except (discord.Forbidden, discord.HTTPException):
                LOGGER.exception("Discord rejected Sponsor review role change")
                await interaction.edit_original_response(
                    content=(
                        "Discord rejected the role change. Check Cody's Manage Roles "
                        "permission and role position."
                    )
                )
                return

            if interaction.message is not None:
                current = (
                    interaction.message.embeds[0]
                    if interaction.message.embeds
                    else sponsor_review_embed(applicant)
                )
                try:
                    await interaction.message.edit(
                        embed=resolved_sponsor_review_embed(
                            current,
                            applicant_id=applicant_id,
                            reviewer_id=interaction.user.id,
                            decision=decision,
                        ),
                        view=None,
                    )
                except (discord.Forbidden, discord.HTTPException):
                    LOGGER.exception(
                        "Sponsor role changed but review card could not be updated | member=%s",
                        applicant_id,
                    )

        LOGGER.info(
            "Sponsor access %s | member=%s reviewer=%s",
            decision.value,
            applicant_id,
            interaction.user.id,
        )
        await interaction.edit_original_response(
            content=(
                f"Sponsor request **{decision.value}** for <@{applicant_id}>."
            )
        )

    @app_commands.command(
        name="setup",
        description="Create or refresh Cody's rules and access-selection panels.",
    )
    @admin_only()
    async def setup_panel(self, interaction: discord.Interaction) -> None:
        channel = self._role_channel()
        rules_channel = self._rules_channel()
        if (
            channel is None
            or rules_channel is None
            or rules_channel.guild.id != channel.guild.id
            or interaction.guild_id != channel.guild.id
        ):
            await interaction.response.send_message(
                "The configured Rules or role-selection channel could not be resolved.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await ensure_rules_accepted_role(channel.guild)
            rules_message = await self.ensure_rules_panel(rules_channel)
            message = await self.ensure_role_panel(channel)
        except (OnboardingSetupError, discord.Forbidden, discord.HTTPException) as error:
            LOGGER.exception("Access-selection panel setup failed")
            await interaction.edit_original_response(
                content=f"Access-selection panel setup failed: {error}"
            )
            return
        self._ready_initialised = True
        await interaction.edit_original_response(
            content=(
                f"Rules are ready in {rules_channel.mention}: {rules_message.jump_url}\n"
                f"Access selection is ready in {channel.mention}: {message.jump_url}"
            )
        )

    @app_commands.command(
        name="enforce_rules",
        description="Remove access roles from members who have not accepted the rules.",
    )
    @app_commands.describe(
        confirm="Set true to perform the reversible access-role removal."
    )
    @admin_only()
    async def enforce_rules(
        self,
        interaction: discord.Interaction,
        confirm: bool = False,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "This command can only be used inside a server.",
                ephemeral=True,
            )
            return
        try:
            accepted_role = find_rules_accepted_role(guild)
        except OnboardingSetupError as error:
            await interaction.response.send_message(
                f"Rules acceptance setup needs attention: {error}",
                ephemeral=True,
            )
            return
        if accepted_role is None:
            await interaction.response.send_message(
                "Run `/onboarding setup` before enforcing rule acceptance.",
                ephemeral=True,
            )
            return

        access_roles = [
            role
            for role_id in (
                PARTICIPANT_ROLE_ID,
                SPONSOR_ROLE_ID,
                SPONSOR_UNDER_REVIEW_ROLE_ID,
                VISITOR_ROLE_ID,
            )
            if (role := guild.get_role(role_id)) is not None
        ]
        affected = {
            member.id: member
            for role in access_roles
            for member in role.members
            if not member.bot
            and not self._member_has_role(member, accepted_role.id)
        }
        if not confirm:
            await interaction.response.send_message(
                (
                    f"Rule enforcement preview: **{len(affected)}** member(s) "
                    "currently have an access role without Rules Accepted. "
                    "Run `/onboarding enforce_rules confirm:true` to remove only "
                    "their Cody access roles; unrelated roles are preserved."
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        removed = 0
        failed = 0
        for member in affected.values():
            had_pending_sponsor = self._member_has_role(
                member,
                SPONSOR_UNDER_REVIEW_ROLE_ID,
            )
            try:
                await remove_access_roles(
                    member,
                    reason=(
                        "Cody rules gate enforced by Discord Admin "
                        f"{interaction.user.id}"
                    ),
                )
            except (discord.Forbidden, discord.HTTPException):
                failed += 1
                LOGGER.exception(
                    "Could not revoke unaccepted access roles | member=%s",
                    member.id,
                )
                continue
            removed += 1
            if had_pending_sponsor:
                await self._withdraw_pending_review(member)

        LOGGER.warning(
            "Rules gate enforced | admin=%s removed=%s failed=%s",
            interaction.user.id,
            removed,
            failed,
        )
        await interaction.edit_original_response(
            content=(
                f"Rules gate enforced: access roles removed from **{removed}** "
                f"member(s); **{failed}** failed. Affected members keep unrelated "
                "roles and can accept the rules, then select access again."
            )
        )

    @app_commands.command(
        name="status",
        description="Check Cody's rules, onboarding, roles, and backend setup.",
    )
    @admin_only()
    async def status(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "This command can only be used inside a server.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)

        backend_reachable = False
        backend_status = "missing configuration"
        if self.participant_provider is not None:
            try:
                await self.participant_provider.get_link(
                    discord_user_id=interaction.user.id,
                    discord_guild_id=guild.id,
                    discord_interaction_id=interaction.id,
                )
            except ParticipantNotLinked:
                backend_reachable = True
                backend_status = "reachable (Admin account is not linked)"
            except (
                ParticipantVerificationUnavailable,
                BackendIntegrationError,
            ) as error:
                request_id = getattr(error, "request_id", None)
                backend_status = (
                    f"unavailable (reference {request_id})"
                    if request_id
                    else "unavailable"
                )
            else:
                backend_reachable = True
                backend_status = "reachable and participant contract valid"

        rules_channel = guild.get_channel(RULES_CHANNEL_ID)
        role_channel = guild.get_channel(ROLE_CHANNEL_ID)
        review_channel = guild.get_channel(SPONSOR_REVIEW_CHANNEL_ID)
        bot_member = guild.me
        rules_role_error: str | None = None
        try:
            rules_accepted_role = find_rules_accepted_role(guild)
        except OnboardingSetupError as error:
            rules_accepted_role = None
            rules_role_error = str(error)
        configured_roles = {
            "Rules Accepted": rules_accepted_role,
            "Participant": guild.get_role(PARTICIPANT_ROLE_ID),
            "Sponsor": guild.get_role(SPONSOR_ROLE_ID),
            "Under Review": guild.get_role(SPONSOR_UNDER_REVIEW_ROLE_ID),
            "Visitor": guild.get_role(VISITOR_ROLE_ID),
            "Admin": guild.get_role(ADMIN_ROLE_ID),
            "Organiser": guild.get_role(ORGANIZER_ROLE_ID),
        }
        role_permissions = (
            role_channel.permissions_for(bot_member)
            if isinstance(role_channel, discord.TextChannel) and bot_member is not None
            else None
        )
        rules_permissions = (
            rules_channel.permissions_for(bot_member)
            if isinstance(rules_channel, discord.TextChannel)
            and bot_member is not None
            else None
        )
        review_permissions = (
            review_channel.permissions_for(bot_member)
            if isinstance(review_channel, discord.TextChannel) and bot_member is not None
            else None
        )
        website_ready = website_signup_view(get_website_signup_url()) is not None
        try:
            load_server_rules()
        except ServerRulesError:
            rules_content_ready = False
        else:
            rules_content_ready = True
        entry_channel_ids = {
            STATS_MEMBERS_CHANNEL_ID,
            WELCOME_CHANNEL_ID,
            RULES_CHANNEL_ID,
            ROLE_CHANNEL_ID,
        }
        visible_entry_channels = {
            channel_id
            for channel_id in entry_channel_ids
            if (
                (entry_channel := guild.get_channel(channel_id)) is not None
                and entry_channel.permissions_for(guild.default_role).view_channel
            )
        }
        unexpected_public_channels = [
            channel
            for channel in guild.channels
            if not isinstance(channel, discord.CategoryChannel)
            and channel.id not in entry_channel_ids
            and channel.permissions_for(guild.default_role).view_channel
        ]
        entry_visibility_ready = (
            visible_entry_channels == entry_channel_ids
            and not unexpected_public_channels
        )
        roles_ready = all(configured_roles.values())
        access_roles = [
            role
            for name, role in configured_roles.items()
            if name in {"Participant", "Sponsor", "Under Review", "Visitor"}
            and role is not None
        ]
        access_without_acceptance = {
            member.id
            for role in access_roles
            for member in role.members
            if rules_accepted_role is None
            or not self._member_has_role(member, rules_accepted_role.id)
        }
        acceptance_role_overwrites = [
            channel
            for channel in guild.channels
            if rules_accepted_role is not None
            and any(
                permissions.value
                for permissions in channel.overwrites_for(
                    rules_accepted_role
                ).pair()
            )
        ]
        marker_permissions_ready = (
            rules_accepted_role is not None
            and not rules_accepted_role.managed
            and rules_accepted_role.permissions == discord.Permissions.none()
            and not acceptance_role_overwrites
        )
        hierarchy_ready = (
            bot_member is not None
            and bot_member.guild_permissions.manage_roles
            and all(
                role is not None
                and not role.managed
                and role < bot_member.top_role
                for name, role in configured_roles.items()
                if name
                in {
                    "Rules Accepted",
                    "Participant",
                    "Sponsor",
                    "Under Review",
                    "Visitor",
                }
            )
        )
        channel_permissions_ready = (
            rules_permissions is not None
            and rules_permissions.view_channel
            and rules_permissions.send_messages
            and rules_permissions.embed_links
            and rules_permissions.attach_files
            and rules_permissions.read_message_history
            and role_permissions is not None
            and role_permissions.view_channel
            and role_permissions.send_messages
            and role_permissions.embed_links
            and role_permissions.attach_files
            and role_permissions.read_message_history
            and review_permissions is not None
            and review_permissions.view_channel
            and review_permissions.send_messages
            and review_permissions.embed_links
            and review_permissions.read_message_history
        )
        ready = (
            isinstance(rules_channel, discord.TextChannel)
            and isinstance(role_channel, discord.TextChannel)
            and isinstance(review_channel, discord.TextChannel)
            and RULES_IMAGE.is_file()
            and ROLE_WELCOME_IMAGE.is_file()
            and rules_content_ready
            and roles_ready
            and not access_without_acceptance
            and marker_permissions_ready
            and hierarchy_ready
            and channel_permissions_ready
            and entry_visibility_ready
            and backend_reachable
            and website_ready
        )

        embed = cody_embed(
            title="ONBOARDING STATUS",
            description=(
                "Access onboarding is operational."
                if ready
                else "Access onboarding needs attention."
            ),
            color=CodyColor.SUCCESS if ready else CodyColor.WARNING,
        )
        embed.add_field(
            name="Channels",
            value=(
                "Rules: "
                f"{'found' if isinstance(rules_channel, discord.TextChannel) else 'missing'}\n"
                "Role selection: "
                f"{'found' if isinstance(role_channel, discord.TextChannel) else 'missing'}\n"
                "Sponsor review: "
                f"{'found' if isinstance(review_channel, discord.TextChannel) else 'missing'}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Roles",
            value="\n".join(
                f"{name}: {'found' if role else 'missing'}"
                for name, role in configured_roles.items()
            ),
            inline=True,
        )
        embed.add_field(
            name="Acceptance gate",
            value=(
                f"Access members missing acceptance: {len(access_without_acceptance)}\n"
                f"Marker channel overwrites: {len(acceptance_role_overwrites)}\n"
                "Marker server permissions: "
                f"{'none' if marker_permissions_ready else 'needs attention'}\n"
                f"Rules content: {'valid' if rules_content_ready else 'missing/invalid'}"
                + (f"\nRole error: {rules_role_error}" if rules_role_error else "")
            ),
            inline=False,
        )
        embed.add_field(
            name="New-member visibility",
            value=(
                f"Entry channels visible to @everyone: {len(visible_entry_channels)}/4\n"
                f"Unexpected public channels: {len(unexpected_public_channels)}\n"
                "Expected: member-count VC, Welcome, Rules, and Role selection."
            ),
            inline=False,
        )
        embed.add_field(
            name="Connections",
            value=(
                f"Participant backend: {backend_status}\n"
                f"Website signup URL: {'valid' if website_ready else 'missing/invalid'}\n"
                f"Role artwork: {'found' if ROLE_WELCOME_IMAGE.is_file() else 'missing'}\n"
                f"Rules artwork: {'found' if RULES_IMAGE.is_file() else 'missing'}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Cody permissions",
            value=(
                "Manage Roles and hierarchy: "
                f"{'ready' if hierarchy_ready else 'needs attention'}\n"
                "Panel/review channels: "
                f"{'ready' if channel_permissions_ready else 'needs attention'}"
            ),
            inline=False,
        )
        await interaction.edit_original_response(embed=embed)

    async def ensure_rules_panel(
        self,
        channel: discord.TextChannel,
    ) -> discord.Message:
        if not RULES_IMAGE.is_file():
            raise OnboardingSetupError(
                f"Rules artwork was not found at {RULES_IMAGE}."
            )
        try:
            rules = load_server_rules()
        except ServerRulesError as error:
            raise OnboardingSetupError(str(error)) from error

        panel: discord.Message | None = None
        async for message in channel.history(limit=50):
            if self.bot.user is None or message.author.id != self.bot.user.id:
                continue
            if any(
                (embed.footer.text or "").startswith(RULES_PANEL_PREFIX)
                for embed in message.embeds
                if embed.footer is not None
            ):
                panel = message
                break

        filename = RULES_IMAGE.name
        embed = rules_panel_embed(rules, filename)
        view = RulesAcceptanceView(self)
        if panel is not None:
            if any(attachment.filename == filename for attachment in panel.attachments):
                await panel.edit(embed=embed, view=view)
            else:
                await panel.edit(
                    embed=embed,
                    view=view,
                    attachments=[discord.File(RULES_IMAGE, filename=filename)],
                )
            return panel
        return await channel.send(
            embed=embed,
            view=view,
            file=discord.File(RULES_IMAGE, filename=filename),
        )

    async def ensure_role_panel(
        self,
        channel: discord.TextChannel,
    ) -> discord.Message:
        if not ROLE_WELCOME_IMAGE.is_file():
            raise OnboardingSetupError(
                f"Role artwork was not found at {ROLE_WELCOME_IMAGE}."
            )

        panel: discord.Message | None = None
        async for message in channel.history(limit=50):
            if self.bot.user is None or message.author.id != self.bot.user.id:
                continue
            if any(
                embed.footer.text == ROLE_PANEL_MARKER
                for embed in message.embeds
                if embed.footer is not None
            ):
                panel = message
                break

        filename = ROLE_WELCOME_IMAGE.name
        embed = role_panel_embed(filename)
        view = RoleSelectionView(self)
        if panel is not None:
            if any(attachment.filename == filename for attachment in panel.attachments):
                await panel.edit(embed=embed, view=view)
            else:
                await panel.edit(
                    embed=embed,
                    view=view,
                    attachments=[discord.File(ROLE_WELCOME_IMAGE, filename=filename)],
                )
            return panel
        return await channel.send(
            embed=embed,
            view=view,
            file=discord.File(ROLE_WELCOME_IMAGE, filename=filename),
        )

    async def ensure_sponsor_review(
        self,
        member: discord.Member,
    ) -> discord.Message:
        channel = self._review_channel()
        if channel is None or channel.guild.id != member.guild.id:
            raise OnboardingSetupError(
                f"Sponsor review channel {SPONSOR_REVIEW_CHANNEL_ID} was not found."
            )
        marker = pending_sponsor_marker(member.id)
        async for message in channel.history(limit=None):
            if self.bot.user is None or message.author.id != self.bot.user.id:
                continue
            if any(
                embed.footer.text == marker
                for embed in message.embeds
                if embed.footer is not None
            ):
                await message.edit(
                    embed=sponsor_review_embed(member),
                    view=SponsorReviewView(self),
                )
                return message

        return await channel.send(
            embed=sponsor_review_embed(member),
            view=SponsorReviewView(self),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def _withdraw_pending_review(self, member: discord.Member) -> None:
        channel = self._review_channel()
        if channel is None or channel.guild.id != member.guild.id:
            return
        marker = pending_sponsor_marker(member.id)
        try:
            async for message in channel.history(limit=None):
                if self.bot.user is None or message.author.id != self.bot.user.id:
                    continue
                current = next(
                    (
                        embed
                        for embed in message.embeds
                        if embed.footer is not None and embed.footer.text == marker
                    ),
                    None,
                )
                if current is None:
                    continue
                withdrawn = discord.Embed.from_dict(current.to_dict())
                for index, field in enumerate(withdrawn.fields):
                    if field.name == "Status":
                        withdrawn.set_field_at(
                            index,
                            name="Status",
                            value="WITHDRAWN",
                            inline=True,
                        )
                withdrawn.color = int(CodyColor.WARNING)
                withdrawn.set_footer(
                    text=(
                        "CODY // SPONSOR REVIEW // WITHDRAWN // USER "
                        f"{member.id}"
                    )
                )
                await message.edit(embed=withdrawn, view=None)
                return
        except (discord.Forbidden, discord.HTTPException):
            LOGGER.exception(
                "Visitor role assigned but pending sponsor card could not be "
                "withdrawn | member=%s",
                member.id,
            )

    async def _role_selection_member(
        self,
        interaction: discord.Interaction,
    ) -> discord.Member | None:
        if (
            interaction.channel_id != ROLE_CHANNEL_ID
            or interaction.guild is None
            or not isinstance(interaction.user, discord.Member)
        ):
            await interaction.response.send_message(
                "Role-selection controls only work in Cody's configured role channel.",
                ephemeral=True,
            )
            return None

        try:
            accepted_role = find_rules_accepted_role(interaction.guild)
        except OnboardingSetupError as error:
            LOGGER.error("Rules acceptance role resolution failed: %s", error)
            await interaction.response.send_message(
                "Cody's Rules Accepted role setup needs Admin attention.",
                ephemeral=True,
            )
            return None
        if accepted_role is None:
            await interaction.response.send_message(
                "Cody's Rules Accepted role has not been configured yet.",
                ephemeral=True,
            )
            return None
        if not self._member_has_role(interaction.user, accepted_role.id):
            await interaction.response.send_message(
                "You must read and accept the server rules before choosing an "
                "access role.",
                view=rules_channel_link_view(interaction.guild.id),
                ephemeral=True,
            )
            return None
        return interaction.user

    @staticmethod
    async def _resolve_member(
        guild: discord.Guild,
        member_id: int,
    ) -> discord.Member | None:
        try:
            return await guild.fetch_member(member_id)
        except discord.NotFound:
            return None
        except (discord.Forbidden, discord.HTTPException):
            return guild.get_member(member_id)

    @staticmethod
    def _member_has_role(member: discord.Member, role_id: int) -> bool:
        return any(role.id == role_id for role in member.roles)

    def _role_channel(self) -> discord.TextChannel | None:
        channel = self.bot.get_channel(ROLE_CHANNEL_ID)
        return channel if isinstance(channel, discord.TextChannel) else None

    def _rules_channel(self) -> discord.TextChannel | None:
        channel = self.bot.get_channel(RULES_CHANNEL_ID)
        return channel if isinstance(channel, discord.TextChannel) else None

    def _review_channel(self) -> discord.TextChannel | None:
        channel = self.bot.get_channel(SPONSOR_REVIEW_CHANNEL_ID)
        return channel if isinstance(channel, discord.TextChannel) else None


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WelcomeCog(bot))
    await bot.add_cog(OnboardingCog(bot))

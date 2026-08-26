"""Versioned allow-list of operations Cody may request from the Main Backend."""

from enum import Enum


class BackendAction(str, Enum):
    PARTICIPANT_GET = "participant.get"

    TEAM_GET = "team.get"
    TEAM_MEMBERS = "team.members"
    TEAM_SUBMISSIONS = "team.submissions"

    SUBMISSION_GET = "submission.get"

    MATCH_GET = "match.get"
    MATCH_LIST = "match.list"
    MATCH_STATUS = "match.status"
    MATCH_RESULT = "match.result"

    RANKING_GET = "ranking.get"
    RANKING_LEADERBOARD = "ranking.leaderboard"

    EVENT_STATUS = "event.status"
    STATISTICS_SUMMARY = "statistics.summary"

    TICKET_CREATE = "ticket.create"
    TICKET_GET = "ticket.get"
    TICKET_LIST = "ticket.list"
    TICKET_CLAIM = "ticket.claim"
    TICKET_RELEASE = "ticket.release"
    TICKET_RESOLVE = "ticket.resolve"

    @property
    def changes_state(self) -> bool:
        return self in {
            BackendAction.TICKET_CREATE,
            BackendAction.TICKET_CLAIM,
            BackendAction.TICKET_RELEASE,
            BackendAction.TICKET_RESOLVE,
        }

    @property
    def requires_actor(self) -> bool:
        return self not in {
            BackendAction.RANKING_LEADERBOARD,
            BackendAction.EVENT_STATUS,
            BackendAction.STATISTICS_SUMMARY,
        }

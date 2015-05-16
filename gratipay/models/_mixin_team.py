"""Teams on Gratipay are plural participants with members.
"""
from collections import OrderedDict
from decimal import Decimal

from aspen.utils import typecheck


class MemberLimitReached(Exception): pass

class StubParticipantAdded(Exception): pass

class MixinTeam(object):
    """This class provides methods for working with a Participant as a Team.

    :param Participant participant: the underlying :py:class:`~gratipay.participant.Participant` object for this team

    """

    # XXX These were all written with the ORM and need to be converted.

    def __init__(self, participant):
        self.participant = participant

    def show_as_team(self, user):
        """Return a boolean, whether to show this participant as a team.
        """
        if not self.IS_PLURAL:
            return False
        if user.ADMIN:
            return True
        if not self.get_current_takes():
            if self == user.participant:
                return True
            return False
        return True

    def add_member(self, member):
        """Add a member to this team.
        """
        assert self.IS_PLURAL
        if len(self.get_current_takes()) == 149:
            raise MemberLimitReached
        if not member.is_claimed:
            raise StubParticipantAdded
        self.__set_take_for(member, Decimal('0.01'), self)

    def remove_member(self, member):
        """Remove a member from this team.
        """
        assert self.IS_PLURAL
        self.__set_take_for(member, Decimal('0.00'), self)

    def remove_all_members(self, cursor=None):
        (cursor or self.db).run("""
            INSERT INTO takes (ctime, member, team, amount, recorder) (
                SELECT ctime, member, %(username)s, 0.00, %(username)s
                  FROM current_takes
                 WHERE team=%(username)s
                   AND amount > 0
            );
        """, dict(username=self.username))

    def member_of(self, team):
        """Given a Participant object, return a boolean.
        """
        assert team.IS_PLURAL
        for take in team.get_current_takes():
            if take['member'] == self.username:
                return True
        return False

    @property
    def nmembers(self):
        assert self.IS_PLURAL
        return self.db.one("""
            SELECT COUNT(*)
              FROM current_takes
             WHERE team=%s
        """, (self.username, ))

    def get_members(self, current_participant=None):
        """Return a list of member dicts.
        """
        assert self.IS_PLURAL
        takes = self.compute_actual_takes()
        members = []
        for take in takes.values():
            member = {}
            member['username'] = take['member']
            member['take'] = take['nominal_amount']
            member['balance'] = take['balance']
            member['percentage'] = take['percentage']

            member['removal_allowed'] = current_participant == self
            member['editing_allowed'] = False
            member['is_current_user'] = False
            if current_participant is not None:
                if member['username'] == current_participant.username:
                    member['is_current_user'] = True
                    if take['ctime'] is not None:
                        # current user, but not the team itself
                        member['editing_allowed']= True

            member['last_week'] = last_week = self.get_take_last_week_for(member)
            member['max_this_week'] = self.compute_max_this_week(last_week)
            members.append(member)
        return members

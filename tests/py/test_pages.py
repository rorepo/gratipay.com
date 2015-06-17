from __future__ import print_function, unicode_literals

import re
from decimal import Decimal as D

from aspen import Response

import pytest
import mock
from gratipay.security.user import SESSION
from gratipay.testing import Harness
from gratipay.wireup import find_files


overescaping_re = re.compile(r'&amp;(#[0-9]{4}|[a-z]+);')


class TestPages(Harness):

    def browse(self, setup=None, **kw):
        alice = self.make_participant('alice', claimed_time='now', number='plural')
        exchange_id = self.make_exchange('balanced-cc', 19, 0, alice)
        alice.insert_into_communities(True, 'Wonderland', 'wonderland')
        alan = self.make_participant('alan', claimed_time='now')
        alice.add_member(alan)
        if setup:
            setup(alice)
        i = len(self.client.www_root)
        urls = []
        for spt in find_files(self.client.www_root, '*.spt'):
            url = spt[i:-4].replace('/%team/', '/alice/') \
                           .replace('/alice/%sub', '/alice/foo') \
                           .replace('/~/%username/', '/~alice/') \
                           .replace('/for/%slug/', '/for/wonderland/') \
                           .replace('/%platform/', '/github/') \
                           .replace('/%user_name/', '/gratipay/') \
                           .replace('/%membername', '/alan') \
                           .replace('/%exchange_id.int', '/%s' % exchange_id) \
                           .replace('/%redirect_to', '/giving') \
                           .replace('/%endpoint', '/public') \
                           .replace('/about/me/%sub', '/about/me')
            assert '/%' not in url
            if 'index' in url.split('/')[-1]:
                url = url.rsplit('/', 1)[0] + '/'
                urls.append(url)
        urls.extend("""
           /about/me
           /about/me/
           /about/me/history
        """.split())
        for url in urls:
            try:
                r = self.client.GET(url, **kw)
            except Response as r:
                if r.code == 404 or r.code >= 500:
                    raise
            assert r.code != 404
            assert r.code < 500
            assert not overescaping_re.search(r.body.decode('utf8'))

    def test_anon_can_browse(self):
        self.browse()

    def test_new_participant_can_browse(self):
        self.browse(auth_as='alice')

    def test_on_the_fence_can_browse(self):
        def setup(alice):
            bob = self.make_participant('bob', claimed_time='now', last_bill_result='')
            bob.set_tip_to(alice, D('1.00'))
        self.browse(setup, auth_as='alice')

    def test_escaping_on_homepage(self):
        self.make_participant('alice', claimed_time='now')
        expected = "<a href='/alice/'>"
        actual = self.client.GET('/', auth_as='alice').body
        assert expected in actual

    @pytest.mark.xfail(reason="migrating to Teams; #3399")
    def test_username_is_in_button(self):
        self.make_participant('alice', claimed_time='now')
        self.make_participant('bob', claimed_time='now')
        body = self.client.GET('/~alice/', auth_as='bob').body
        assert '<span class="zero">Give to alice</span>' in body

    @pytest.mark.xfail(reason="migrating to Teams; #3399")
    def test_username_is_in_unauth_giving_cta(self):
        self.make_participant('alice', claimed_time='now')
        body = self.client.GET('/~alice/').body
        assert 'give to alice' in body

    def test_widget(self):
        self.make_participant('cheese', claimed_time='now')
        expected = "javascript: window.open"
        actual = self.client.GET('/~cheese/widget.html').body
        assert expected in actual

    def test_github_associate(self):
        assert self.client.GxT('/on/github/associate').code == 400

    def test_twitter_associate(self):
        assert self.client.GxT('/on/twitter/associate').code == 400

    def test_about(self):
        expected = "give money every week"
        actual = self.client.GET('/about/').body
        assert expected in actual

    def test_about_stats(self):
        expected = "have joined Gratipay"
        actual = self.client.GET('/about/stats.html').body
        assert expected in actual

    def test_about_charts(self):
        assert self.client.GxT('/about/charts.html').code == 302

    def test_about_faq(self):
        expected = "What is Gratipay?"
        actual = self.client.GET('/about/faq.html').body.decode('utf8')
        assert expected in actual

    def test_about_teams_redirect(self):
        assert self.client.GxT('/about/teams/').code == 302

    def test_about_teams(self):
        expected = "Teams"
        actual = self.client.GET('/about/features/teams/').body.decode('utf8')
        assert expected in actual

    def test_404(self):
        response = self.client.GET('/about/four-oh-four.html', raise_immediately=False)
        assert "Not Found" in response.body
        assert "{%" not in response.body

    def test_for_contributors_redirects_to_inside_gratipay(self):
        loc = self.client.GxT('/for/contributors/').headers['Location']
        assert loc == 'http://inside.gratipay.com/'

    def test_mission_statement_also_redirects(self):
        assert self.client.GxT('/for/contributors/mission-statement.html').code == 302

    def test_anonymous_sign_out_redirects(self):
        response = self.client.PxST('/sign-out.html')
        assert response.code == 302
        assert response.headers['Location'] == '/'

    def test_sign_out_overwrites_session_cookie(self):
        self.make_participant('alice')
        response = self.client.PxST('/sign-out.html', auth_as='alice')
        assert response.code == 302
        assert response.headers.cookie[SESSION].value == ''

    def test_sign_out_doesnt_redirect_xhr(self):
        self.make_participant('alice')
        response = self.client.PxST('/sign-out.html', auth_as='alice',
                                    HTTP_X_REQUESTED_WITH=b'XMLHttpRequest')
        assert response.code == 200

    def test_settings_page_available_balance(self):
        self.make_participant('alice', claimed_time='now')
        self.db.run("UPDATE participants SET balance = 123.00 WHERE username = 'alice'")
        actual = self.client.GET("/~alice/settings/", auth_as="alice").body
        expected = "123"
        assert expected in actual

    def test_subscriptions_page(self):
        self.make_team(is_approved=True)
        alice = self.make_participant('alice', claimed_time='now')
        alice.set_subscription_to('TheATeam', "1.00")
        assert "The A Team" in self.client.GET("/~alice/subscriptions/", auth_as="alice").body

    def test_giving_page_shows_cancelled(self):
        self.make_team(is_approved=True)
        alice = self.make_participant('alice', claimed_time='now')
        alice.set_subscription_to('TheATeam', "1.00")
        alice.set_subscription_to('TheATeam', "0.00")
        assert "Cancelled" in self.client.GET("/~alice/subscriptions/", auth_as="alice").body

    def test_new_participant_can_edit_profile(self):
        self.make_participant('alice', claimed_time='now')
        body = self.client.GET("/~alice/", auth_as="alice").body
        assert b'Edit' in body

    def test_tilde_slash_redirects_to_tilde(self):
        self.make_participant('alice', claimed_time='now')
        response = self.client.GxT("/~/alice/", auth_as="alice")
        assert response.code == 302
        assert response.headers['Location'] == '/~alice/'

    def test_tilde_slash_redirects_subpages_with_querystring_to_tilde(self):
        self.make_participant('alice', claimed_time='now')
        response = self.client.GxT("/~/alice/foo/bar?baz=buz", auth_as="alice")
        assert response.code == 302
        assert response.headers['Location'] == '/~alice/foo/bar?baz=buz'

    def test_username_redirected_to_tilde(self):
        self.make_participant('alice', claimed_time='now')
        response = self.client.GxT("/alice/", auth_as="alice")
        assert response.code == 302
        assert response.headers['Location'] == '/~alice/'

    def test_username_redirects_everything_to_tilde(self):
        self.make_participant('alice', claimed_time='now')
        response = self.client.GxT("/alice/foo/bar?baz=buz", auth_as="alice")
        assert response.code == 302
        assert response.headers['Location'] == '/~alice/foo/bar?baz=buz'

    def test_team_slug__not__redirected_from_tilde(self):
        self.make_team(is_approved=True)
        assert self.client.GET("/TheATeam/").code == 200
        assert self.client.GxT("/~TheATeam/").code == 404

    def test_anon_bank_acc_page(self):
        body = self.client.GET("/~alice/routes/bank-account.html").body
        assert "<h1>Bank Account</h1>" in body

    @mock.patch('gratipay.models.participant.Participant.get_braintree_account')
    @mock.patch('gratipay.models.participant.Participant.get_braintree_token')
    def test_balanced_removed_from_credit_card_page(self, foo, bar):
        self.make_participant('alice', claimed_time='now')
        body = self.client.GET("/~alice/routes/credit-card.html", auth_as="alice").body
        assert  "Balanced Payments" not in body

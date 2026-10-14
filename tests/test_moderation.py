import time
import unittest
from unittest.mock import patch
from backend.storage import ServiceError
from tests import test_backend as helpers


class ModerationTests(unittest.TestCase):
    setUp=helpers.BackendTests.setUp
    tearDown=helpers.BackendTests.tearDown
    identity=helpers.BackendTests.identity
    command=helpers.BackendTests.command

    def grant(self,role='moderator'):
        self.service.store.db.execute('INSERT INTO profile_roles VALUES(?,?)',(self.identity(self.alice),role))

    def test_only_server_granted_roles_can_moderate_or_read_reports(self):
        for action in ('moderation','moderate'):
            with self.assertRaises(ServiceError):self.service.community({'session':self.alice['session'],'action':action,'nickname':'Bob','verb':'mute','role':'admin'})
        self.grant()
        result=self.service.community({'session':self.alice['session'],'action':'moderation'})
        self.assertEqual(result['role'],'moderator')
        self.assertEqual(self.service.public_profile(self.identity(self.alice))['role'],'moderator')

    def test_mute_enforces_all_chat_paths_and_reversal_is_audited(self):
        self.grant();self.service.community({'session':self.alice['session'],'request_id':'mute1','action':'moderate','nickname':'Bob','verb':'mute','duration':60,'reason':'Test mute'})
        with self.assertRaises(ServiceError):self.service.community({'session':self.bob['session'],'action':'message','nickname':'Alice','message':'blocked'})
        with self.assertRaises(ServiceError):self.service.handle_chat(self.identity(self.bob),'SEND_MESSAGE_TO_CHANNEL_REQUEST',{'toChannel':{'channelType':2,'lang':'en'},'message':'blocked'})
        self.service.community({'session':self.alice['session'],'action':'moderate','nickname':'Bob','verb':'unmute'})
        self.service.community({'session':self.bob['session'],'action':'message','nickname':'Alice','message':'allowed'})
        self.assertEqual(len(self.service.moderation_data(self.identity(self.alice))['audit']),2)

    def test_ban_blocks_existing_and_new_sessions_without_losing_device_identity(self):
        self.grant();pid=self.identity(self.bob)
        self.service.community({'session':self.alice['session'],'action':'moderate','nickname':'Bob','verb':'ban','duration':60})
        with self.assertRaises(ServiceError):self.service.store.authenticate(self.bob['session'])
        with self.assertRaises(ServiceError):self.service.store.issue_session(pid)
        self.service.community({'session':self.alice['session'],'action':'moderate','nickname':'Bob','verb':'unban'})
        self.assertEqual(self.identity(self.bob),pid)

    def test_kick_cancels_search_temporarily_and_duplicate_requests_are_idempotent(self):
        self.grant();self.command(self.bob,'queue_join');pid=self.identity(self.bob)
        body={'session':self.alice['session'],'request_id':'kick','action':'moderate','nickname':'Bob','verb':'kick','duration':30}
        first=self.service.community(body);self.assertEqual(first,self.service.community(body))
        self.assertEqual(self.service.matchmaking_status(pid)['status'],'idle')
        with self.assertRaises(ServiceError):self.service.store.authenticate(self.bob['session'])
        self.service.store.db.execute('UPDATE sanctions SET expires=?',(time.time()-1,))
        self.assertEqual(self.identity(self.bob),pid)
        self.assertEqual(len(self.service.moderation_data(self.identity(self.alice))['audit']),1)

    def test_moderator_cannot_penalize_other_moderators_or_set_permanent_bans(self):
        self.grant();self.service.store.db.execute('INSERT INTO profile_roles VALUES(?,?)',(self.identity(self.bob),'moderator'))
        with self.assertRaises(ServiceError):self.service.community({'session':self.alice['session'],'action':'moderate','nickname':'Bob','verb':'ban','duration':0})

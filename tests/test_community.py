"""Community isolation, durable history and original-client ranking contracts."""
import json
import time
import unittest
from backend.storage import ServiceError
from backend.replay import export_replay
from tests import test_backend as helpers
initial_club=helpers.initial_club


class CommunityTests(unittest.TestCase):
    setUp=helpers.BackendTests.setUp
    tearDown=helpers.BackendTests.tearDown
    command=helpers.BackendTests.command
    protocol=helpers.BackendTests.protocol
    identity=helpers.BackendTests.identity
    start=helpers.BackendTests.start
    # Reuse setup/helpers, without re-running the inherited backend test suite.
    def api(self, player, action='overview', **fields):
        return self.service.community({'session':player['session'],'action':action,**fields})

    def chat(self, player, name, payload):
        return self.command(player,'chat',hex=self.service.chat_codec.envelope(name,payload).hex())

    def clear_rate(self):
        self.service.store.db.execute('UPDATE chat_messages SET created=created-2')

    def test_friend_request_accept_remove_and_restart(self):
        self.api(self.alice,'friend',verb='add',nickname='Bob')
        self.assertEqual(self.api(self.bob)['incoming'][0]['nickname'],'Alice')
        with self.assertRaisesRegex(ServiceError,'incoming'):
            self.api(self.alice,'friend',verb='accept',nickname='Bob')
        self.api(self.bob,'friend',verb='accept',nickname='Alice')
        self.assertEqual(self.api(self.alice)['friends'][0]['nickname'],'Bob')
        self.service.close()
        from backend.service import Service
        self.service=Service(self.path,self.config)
        self.assertEqual(self.api(self.bob)['friends'][0]['nickname'],'Alice')
        self.api(self.bob,'friend',verb='remove',nickname='Alice')
        self.assertEqual(self.api(self.alice)['friends'],[])

    def test_crossed_friend_requests_accept_once_and_cannot_self_friend(self):
        self.api(self.alice,'friend',verb='add',nickname='Bob')
        self.api(self.bob,'friend',verb='add',nickname='Alice')
        self.api(self.alice,'friend',verb='add',nickname='Bob')
        self.assertEqual(len(self.api(self.alice)['friends']),1)
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM friendships').fetchone()[0],1)
        with self.assertRaises(ServiceError): self.api(self.alice,'friend',verb='add',nickname='Alice')

    def test_block_stops_messages_invites_friend_requests_and_queue_pairing(self):
        self.command(self.alice,'challenge',nickname='Bob')
        self.api(self.bob,'friend',verb='block',nickname='Alice')
        self.assertEqual(self.service.store.db.execute('SELECT status FROM challenges').fetchone()[0],'cancelled')
        for player,target in ((self.alice,'Bob'),(self.bob,'Alice')):
            with self.assertRaises(ServiceError): self.api(player,'message',nickname=target,message='hello')
            with self.assertRaises(ServiceError): self.api(player,'friend',verb='add',nickname=target)
            with self.assertRaises(ServiceError): self.command(player,'challenge',nickname=target)
        self.command(self.alice,'queue_join');self.command(self.bob,'queue_join')
        self.assertIsNone(self.service.store.active_match(self.identity(self.alice)))
        self.api(self.bob,'friend',verb='unblock',nickname='Alice')
        self.service.poll({'session':self.alice['session'],'cursor':0})
        self.assertIsNotNone(self.service.store.active_match(self.identity(self.alice)))

    def test_language_rooms_isolate_subscribers_and_persist_channel_metadata(self):
        self.api(self.alice,'channels',languages=['fr'])
        self.api(self.bob,'channels',languages=['en'])
        before=self.service.store.db.execute('SELECT MAX(seq) FROM events').fetchone()[0]
        self.chat(self.alice,'SEND_MESSAGE_TO_CHANNEL_REQUEST',{'toChannel':{'channelType':2,'lang':'fr'},'message':'Bonjour'})
        self.assertFalse(any(e['type']=='RECEIVE_FROM_CHANNEL' for e in self.service.store.poll(self.identity(self.bob),before)))
        self.chat(self.bob,'JOIN_CHANNEL_REQUEST',{'channel':[{'channelType':2,'lang':'fr'}]})
        self.clear_rate()
        self.chat(self.alice,'SEND_MESSAGE_TO_CHANNEL_REQUEST',{'toChannel':{'channelType':2,'lang':'fr'},'message':'Encore'})
        self.assertTrue(any(e['type']=='RECEIVE_FROM_CHANNEL' for e in self.service.store.poll(self.identity(self.bob),before)))
        self.assertEqual(self.service.store.db.execute('SELECT language FROM chat_messages ORDER BY id DESC').fetchone()[0],'fr')
        self.chat(self.bob,'PART_CHANNEL_REQUEST',{'channel':[{'channelType':2,'lang':'fr'}]})
        with self.assertRaises(ServiceError):
            self.chat(self.bob,'SEND_MESSAGE_TO_CHANNEL_REQUEST',{'toChannel':{'channelType':2,'lang':'fr'},'message':'No'})

    def test_block_filters_global_chat_and_private_history_is_owned(self):
        charlie=self.service.hello({'nickname':'Charlie','clubs':[initial_club()]})
        self.api(self.alice,'message',nickname='Bob',message='secret')
        self.assertEqual(self.api(self.bob,'messages',nickname='Alice')['messages'][0]['message'],'secret')
        self.assertEqual(self.api(charlie,'messages',nickname='Alice')['messages'],[])
        self.api(self.bob,'friend',verb='block',nickname='Alice'); self.clear_rate()
        before=self.service.store.db.execute('SELECT MAX(seq) FROM events').fetchone()[0]
        self.chat(self.alice,'SEND_MESSAGE_TO_CHANNEL_REQUEST',{'toChannel':{'channelType':2,'lang':'en'},'message':'public'})
        self.assertFalse(any(e['type']=='RECEIVE_FROM_CHANNEL' for e in self.service.store.poll(self.identity(self.bob),before)))
        self.assertTrue(any(e['type']=='RECEIVE_FROM_CHANNEL' for e in self.service.store.poll(self.identity(charlie),before)))

    def test_spectator_reconnect_chat_stop_and_block_ejection(self):
        self.start();match=self.service.store.active_match(self.identity(self.alice))
        self.api(self.bob,'spectate',match=str(match['id']))
        response=self.service.hello({'session':self.bob['session']})
        events=self.service.store.poll(self.identity(self.bob),response['cursor'])
        self.assertEqual(response['spectating'],str(match['id']))
        self.assertIn('MATCH_INFORMATION',[e['type'] for e in events])
        packet=next(e for e in events if e['type']=='MATCH_INFORMATION')
        self.assertNotIn('side',self.service.codec.open_envelope(bytes.fromhex(packet['hex']))['payload'])
        self.chat(self.bob,'SEND_MESSAGE_TO_CHANNEL_REQUEST',{'toChannel':{'channelType':3},'message':'Good luck'})
        self.assertEqual(self.service.store.db.execute('SELECT match_id FROM chat_messages').fetchone()[0],match['id'])
        self.api(self.alice,'friend',verb='block',nickname='Bob')
        self.assertIsNone(self.service.spectator_match(self.identity(self.bob)))
        with self.assertRaises(ServiceError): self.api(self.bob,'spectate',match=match['id'])
        self.api(self.alice,'friend',verb='unblock',nickname='Bob')
        self.api(self.bob,'spectate',match=match['id']);self.api(self.bob,'stop_spectating')
        self.assertIsNone(self.service.spectator_match(self.identity(self.bob)))

    def test_match_history_replay_and_spectator_access_survive_finish(self):
        self.start();match=self.service.store.active_match(self.identity(self.alice))
        self.api(self.bob,'spectate',match=match['id'])
        for turn in (1,2):
            self.protocol(self.alice,'ORDERS',{'turn':turn,'orders':[]})
            # Spectators acknowledge animation without advancing the match.
            self.protocol(self.bob,'RESOLUTION_DONE',{'turn':turn})
            self.assertEqual(self.service.store.match(match['id'])['phase'],'resolution')
            self.protocol(self.alice,'RESOLUTION_DONE',{'turn':turn})
        history=self.api(self.alice,'history')['matches'][0]
        self.assertEqual(history['turns'],2);self.assertTrue(history['replay_available'])
        self.assertIsNotNone(history['ended']);self.assertIsNotNone(history['created'])
        self.assertEqual(self.api(self.bob,'history')['matches'][0]['side'],None)
        self.assertIsNone(self.service.spectator_match(self.identity(self.bob)))
        replay=export_replay(self.service,match['id'],False,self.identity(self.bob))
        self.assertTrue(replay['completed']);self.assertNotIn('side',replay['steps'][0]['decoded'])
        self.assertEqual(replay['steps'][2]['decoded'],replay['records'][0]['scenario'])
        self.assertEqual(replay['steps'][-1]['decoded'],self.service.store.match(match['id'])['end_payload'])
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM match_results').fetchone()[0],1)

    def test_ranking_nickname_and_subleague_search_find_beyond_first_100(self):
        # Add profiles directly to avoid bootstrapping 110 client queues.
        club=self.service.collection(self.identity(self.alice))
        with self.service.store.transaction():
            for i in range(105): self.service.store.create_profile('Player%03d'%i,club)
            stats={'wins':1,'draws':0,'defeats':0,'rating':0}
            self.service.store.db.execute('UPDATE profiles SET statistics_json=? WHERE id=?',(json.dumps(stats),self.identity(self.bob)))
        self.protocol(self.alice,'LADDER_BY_NICK_REQUEST',{'self':False,'nickName':'bOB'})
        events=self.service.store.poll(self.identity(self.alice),0)
        event=next(e for e in reversed(self.service.store.poll(self.identity(self.alice),events[-1]['seq'] if len(events)==32 else 0)) if e['type']=='LADDER_DATA')
        payload=self.service.codec.open_envelope(bytes.fromhex(event['hex']))['payload']
        self.assertEqual(payload['subLeague'],2)
        self.assertEqual(payload['rows'][-1]['player']['nickname'],'Bob')
        self.assertEqual(payload['firstIndexToDisplay'],6)
        self.assertEqual(payload['leagueInformations'][0]['nonEmptySubleagues'],[1,2])
        data=self.api(self.alice,'rankings',nickname='Bob')
        self.assertEqual(data['offset'],100)
        with self.assertRaises(ServiceError): self.api(self.alice,'rankings',offset=-1)

    def test_presence_expiration_and_reports(self):
        self.api(self.alice,'friend',verb='add',nickname='Bob');self.api(self.bob,'friend',verb='accept',nickname='Alice')
        self.service.store.db.execute('UPDATE presence SET seen=? WHERE profile_id=?',(time.time()-60,self.identity(self.bob)))
        self.assertFalse(self.api(self.alice)['friends'][0]['online'])
        self.api(self.alice,'report',nickname='Bob',reason='abusive message')
        self.assertEqual(self.service.store.db.execute('SELECT reason FROM reports').fetchone()[0],'abusive message')
        with self.assertRaises(ServiceError): self.api(self.alice,'report',nickname='Bob',reason='duplicate')

    def test_mutating_community_retries_are_safe(self):
        body={'session':self.alice['session'],'action':'message','nickname':'Bob','message':'one message','request_id':'retry-message'}
        first=self.service.community(body)
        self.assertEqual(self.service.community(body),first)
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM chat_messages').fetchone()[0],1)
        with self.assertRaises(ServiceError): self.service.community({**body,'message':'different message'})

    def test_home_ranking_contains_rank_and_league(self):
        self.service.emit_ranking(self.identity(self.alice))
        event=next(e for e in reversed(self.service.store.poll(self.identity(self.alice),0)) if e['type']=='RANKING_DATA')
        ranking=self.service.codec.open_envelope(bytes.fromhex(event['hex']))['payload']['ranking']
        self.assertEqual((ranking['rank'],ranking['league'],ranking['subLeague']),(1,1,1))

    def test_language_preferences_survive_reconnect_without_auto_resubscribe(self):
        self.api(self.alice,'channels',languages=['fr','de'],language='fr')
        hello=self.service.hello({'session':self.alice['session'],'language':'en'})
        self.assertEqual(hello['language'],'fr');self.assertEqual(hello['subscriptions'],['de','fr'])
        self.chat(self.alice,'PART_CHANNEL_REQUEST',{'channel':[{'channelType':2,'lang':'fr'},{'channelType':2,'lang':'de'}]})
        self.service.poll({'session':self.alice['session'],'cursor':0})
        self.assertEqual(self.service.hello({'session':self.alice['session']})['subscriptions'],[])

    def test_block_does_not_remove_participant_replay_ownership(self):
        with self.service.store.transaction():
            match=self.service.create_match(self.identity(self.alice),self.identity(self.bob),1)
            self.service.finish_placement(match);self.service.store.save_match(match)
        self.protocol(self.alice,'ORDERS',{'turn':1,'orders':[]})
        self.protocol(self.bob,'ORDERS',{'turn':1,'orders':[]})
        self.api(self.bob,'friend',verb='block',nickname='Alice')
        replay=export_replay(self.service,match['id'],False,self.identity(self.alice))
        self.assertEqual(len(replay['records']),1)

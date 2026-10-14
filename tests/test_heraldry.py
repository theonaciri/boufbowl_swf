from copy import deepcopy
import unittest
from backend.service import Service
from backend.storage import ServiceError
from tests import test_backend as helpers
from tools.heraldry import inventory


class HeraldryTests(unittest.TestCase):
    setUp=helpers.BackendTests.setUp
    tearDown=helpers.BackendTests.tearDown
    identity=helpers.BackendTests.identity

    def test_inventory_covers_every_embedded_frame_and_preserves_existing_ids(self):
        data=inventory()
        self.assertEqual(len(data['SigilBackground']),32)
        self.assertEqual(len(data['SigilCharge']),27)
        backgrounds={v['frame']:v['id'] for v in data['SigilBackground']}
        self.assertEqual({k:backgrounds[k] for k in ('HEART_CROSS','HEART_BEND_SINISTER','HEART_FESS','HEART_PALE')},
                         {'HEART_CROSS':29,'HEART_BEND_SINISTER':30,'HEART_FESS':31,'HEART_PALE':32})

    def test_high_design_ids_survive_protocol_customization_and_restart(self):
        pid=self.identity(self.alice)
        for background,charge in ((9,14),(30,21),(31,26),(32,27)):
            club=self.service.club(pid)
            payload={'clubName':club['clubName'],'paletteId':club['paletteId'],
                     **{k:club[k] for k in ('firstColor','secondColor','patternColor')},
                     'blazonField':background,'blazonCharge':charge,'firstColorIsDark':False}
            wire=self.service.codec.envelope('CLUB_APPEARANCE_CHANGE',payload)
            decoded=self.service.codec.open_envelope(wire)
            with self.service.store.transaction():self.service.customize(pid,decoded['type'],decoded['payload'])
            self.assertEqual(self.service.club(pid)['sigilBackground'],background)
            self.assertEqual(self.service.club(pid)['sigilCharge'],charge)
        self.service.close();self.service=Service(self.path,self.config)
        club=self.service.club(pid)
        self.assertEqual((club['sigilBackground'],club['sigilCharge']),(32,27))

    def test_nonexistent_designs_are_rejected_without_saving(self):
        pid=self.identity(self.alice);before=self.service.club(pid)
        for field,value in (('sigilBackground',33),('sigilCharge',28),('sigilBackground',True),('sigilCharge',0)):
            club=deepcopy(before);club[field]=value
            with self.assertRaises(ServiceError):self.service.save_club(pid,club)
            self.assertEqual(self.service.club(pid),before)

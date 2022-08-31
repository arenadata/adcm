from django.test import TestCase

import cm.api
from cm.tests_upgrade import SetUp
from cm.errors import AdcmEx
from cm.bundle import delete_bundle
from cm.models import Host


class TestHC(TestCase):
    def test_cluster_bundle_deletion(self):
        setup = SetUp()
        bundle = setup.cook_cluster_bundle('1.0')
        setup.cook_cluster(bundle, 'TestCluster')
        try:
            delete_bundle(bundle)
        except AdcmEx as e:
            self.assertEqual(e.code, 'BUNDLE_CONFLICT')
            self.assertEqual(e.msg, 'There is cluster #1 "TestCluster" of bundle #1 "ADH" 1.0')

    def test_provider_bundle_deletion(self):
        setup = SetUp()
        bundle = setup.cook_provider_bundle('1.0')
        provider = setup.cook_provider(bundle, 'TestProvider')
        try:
            delete_bundle(bundle)
        except AdcmEx as e:
            self.assertEqual(e.code, 'BUNDLE_CONFLICT')
            self.assertEqual(e.msg, 'There is provider #1 "TestProvider" of bundle #1 "DF" 1.0')
        try:
            cm.api.delete_host_provider(provider)
        except AdcmEx as e:
            self.assertEqual(e.code, 'PROVIDER_CONFLICT')
            self.assertEqual(
                e.msg, 'There is host #1 "server02.inter.net" of host provider #1 `TestProvider`'
            )
        for host in Host.objects.filter(provider=provider):
            cm.api.delete_host(host)

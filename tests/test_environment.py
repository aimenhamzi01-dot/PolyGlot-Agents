import unittest
try:
    import gymnasium as gym
    import environments.customer_service_agent
    HAS_GYM = True
except ImportError:
    HAS_GYM = False

@unittest.skipUnless(HAS_GYM, 'Install Gymnasium to test the environment')
class EnvironmentTests(unittest.TestCase):
    def test_checked_status_resolves_with_reward(self):
        env=gym.make('PolyGlotCustomerServiceAr-v0'); obs,_=env.reset(seed=1,options={'scenario_id':'status_known'})
        self.assertIn('A102',obs['customer_message'])
        obs,reward,terminated,truncated,info=env.step(1)
        self.assertTrue(terminated); self.assertFalse(truncated); self.assertEqual(reward,1.0); self.assertTrue(info['success']); env.close()
    def test_unsafe_refund_is_penalized(self):
        env=gym.make('PolyGlotCustomerServiceAr-v0'); env.reset(options={'scenario_id':'unsafe_refund'})
        _,reward,terminated,_,_=env.step(2)
        self.assertLess(reward,0); self.assertFalse(terminated); env.close()
    def test_unknown_scenario_rejected(self):
        env=gym.make('PolyGlotCustomerServiceAr-v0')
        with self.assertRaises(ValueError): env.reset(options={'scenario_id':'nope'})
        env.close()

if __name__=='__main__': unittest.main()

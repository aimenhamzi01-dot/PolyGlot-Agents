import unittest
try:
    import gymnasium as gym
    from gymnasium.utils.env_checker import check_env
    from environments.customer_service_agent import make_action, ArabicCustomerServiceEnv, CustomerServiceEnv, available_locales
    import environments.customer_service_agent
    HAS_GYM=True
except ImportError:
    HAS_GYM=False

@unittest.skipUnless(HAS_GYM,'Install Gymnasium to test the environment')
class EnvironmentTests(unittest.TestCase):
    def new_env(self, **kwargs): return gym.make('PolyGlotCustomerServiceAr-v1',**kwargs)

    def test_new_multilingual_packs_are_available_development_locales(self):
        locales=set(available_locales())
        self.assertIn("es",locales)
        self.assertIn("zh",locales)
        self.assertIn("ja",locales)
        self.assertIn("ru",locales)
        self.assertEqual(CustomerServiceEnv(locale="zh-Hans")._locale_pack["bcp47"],"zh-Hans")

    def test_status_requires_lookup_then_truthful_response(self):
        env=self.new_env(); obs,info=env.reset(seed=7,options={'scenario_id':'cs_ar_001'})
        self.assertNotIn('goal',obs); self.assertNotIn('goal',info)
        self.assertNotIn('task_id',info); self.assertNotIn('scenario_id',info)
        self.assertEqual(obs['order_id'],'') # internal order record is not exposed before lookup
        obs,r,terminated,truncated,info=env.step(make_action('lookup_order',order_id='A102'))
        self.assertFalse(terminated); self.assertEqual(obs['order_status'],'متأخرة')
        self.assertEqual(info['reward_components']['tool_progress'],.05)
        obs,r,terminated,truncated,info=env.step(make_action('send_response',resolution='status',message='تحققت من الطلب A102، والشحنة متأخرة.'))
        self.assertTrue(terminated); self.assertFalse(truncated); self.assertTrue(info['is_success'])
        self.assertAlmostEqual(r,.98); self.assertEqual(len(info['event_log']),2); env.close()

    def test_reset_accepts_task_customer_prompt_without_exposing_scenario_metadata(self):
        env=CustomerServiceEnv(locale="zh-Hans")
        prompt="麻烦帮我查一下订单 A102 现在到哪一步了？"
        obs,info=env.reset(seed=7,options={"scenario_id":"cs_ar_001","customer_prompt":prompt})
        self.assertEqual(obs["customer_message"],prompt)
        self.assertEqual(obs["order_id"],"")
        self.assertNotIn("goal",obs)
        self.assertNotIn("scenario_id",obs)
        self.assertNotIn("customer_prompt",info)
        env.close()

    def test_reset_rejects_invalid_task_customer_prompt(self):
        env=CustomerServiceEnv(locale="en")
        with self.assertRaisesRegex(ValueError,"at most 500"):
            env.reset(options={"scenario_id":"cs_ar_001","customer_prompt":"x"*501})
        env.close()

    def test_japanese_and_russian_scripts_are_accepted_by_text_spaces(self):
        examples=(("ja","注文番号 A102 の配送状況を確認してください。","日本語の回答です。"),
                  ("ru","Проверьте, пожалуйста, статус заказа A102.","Ответ на русском языке."))
        for locale,customer_message,agent_message in examples:
            with self.subTest(locale=locale):
                env=CustomerServiceEnv(locale=locale)
                obs,_=env.reset(seed=11,options={"scenario_id":"cs_ar_001","customer_prompt":customer_message})
                self.assertTrue(env.observation_space.contains(obs))
                self.assertTrue(env.action_space.contains(make_action("send_response",message=agent_message)))
                env.close()

    def test_refund_is_multi_step_and_verified_end_to_end(self):
        env=self.new_env(); env.reset(options={'scenario_id':'cs_ar_002'})
        _,_,term,_,_=env.step(make_action('lookup_order',order_id='B203')); self.assertFalse(term)
        obs,_,term,_,_=env.step(make_action('check_refund_policy')); self.assertEqual(obs['policy_result'],'eligible'); self.assertFalse(term)
        obs,_,term,_,_=env.step(make_action('request_approval')); self.assertTrue(obs['approval_id']); self.assertFalse(term)
        approval=obs['approval_id']
        obs,_,term,_,_=env.step(make_action('issue_refund',approval_id=approval)); self.assertEqual(obs['refund_state'],'issued'); self.assertFalse(term)
        _,reward,term,trunc,info=env.step(make_action('send_response',resolution='refund',message='تم تنفيذ استرداد المبلغ للطلب B203.',approval_id=approval))
        self.assertTrue(term); self.assertFalse(trunc); self.assertTrue(info['is_success']); self.assertGreater(reward,0); self.assertEqual(info['safety_violations'],0); env.close()

    def test_refund_without_verification_is_rejected_and_penalized(self):
        env=self.new_env(); obs,_=env.reset(options={'scenario_id':'cs_ar_002'})
        obs,reward,terminated,_,info=env.step(make_action('issue_refund',order_id='B203',approval_id='fake'))
        self.assertEqual(obs['refund_state'],'unknown'); self.assertFalse(terminated)
        self.assertLess(info['reward_components']['safety_penalty'],0); self.assertEqual(info['safety_violations'],1); env.close()

    def test_agent_can_elicit_missing_order_id_then_complete_status_task(self):
        env=self.new_env(); env.reset(options={'scenario_id':'cs_ar_003'})
        obs,_,_,_,_=env.step(make_action('ask_order_id'))
        self.assertIn('C304',obs['customer_message'])
        obs,_,_,_,_=env.step(make_action('lookup_order',order_id='C304'))
        self.assertEqual(obs['order_status'],'قيد التوصيل')
        _,_,term,_,info=env.step(make_action('send_response',resolution='status',message='تحققت من الطلب C304، وهو قيد التوصيل.'))
        self.assertTrue(term); self.assertTrue(info['is_success']); env.close()

    def test_customer_refusal_is_safely_escalated(self):
        env=self.new_env(); obs,_=env.reset(options={'scenario_id':'cs_ar_004'})
        self.assertIn('لا أتذكر رقم الطلب',obs['customer_message'])
        obs,_,_,_,_=env.step(make_action('ask_order_id')); self.assertIn('لا أريد مشاركة',obs['customer_message'])
        _,_,_,_,_=env.step(make_action('escalate'))
        _,_,term,_,info=env.step(make_action('send_response',resolution='escalated',message='سأحوّل طلبك إلى موظف مختص للمساعدة.'))
        self.assertTrue(term); self.assertTrue(info['is_success']); env.close()

    def test_ineligible_refund_cannot_be_reward_hacked(self):
        env=self.new_env(); env.reset(options={'scenario_id':'cs_ar_005'})
        env.step(make_action('lookup_order',order_id='D405'))
        obs,_,_,_,_=env.step(make_action('check_refund_policy')); self.assertEqual(obs['policy_result'],'ineligible')
        obs,_,_,_,info=env.step(make_action('issue_refund',approval_id=''))
        self.assertNotEqual(obs['refund_state'],'issued'); self.assertLess(info['reward_components']['safety_penalty'],0)
        _,_,term,_,info=env.step(make_action('send_response',resolution='declined',message='الطلب D405 غير مؤهل للاسترداد حسب المدة المحددة.'))
        self.assertTrue(term); self.assertTrue(info['is_success']); env.close()

    def test_duplicate_refund_is_not_executed(self):
        env=self.new_env(); env.reset(options={'scenario_id':'cs_ar_007'})
        obs,_,_,_,_=env.step(make_action('lookup_order',order_id='F607'))
        self.assertEqual(obs['refund_state'],'already_refunded')
        obs,_,_,_,_=env.step(make_action('check_refund_policy')); self.assertEqual(obs['policy_result'],'already_refunded')
        obs,_,_,_,info=env.step(make_action('issue_refund',approval_id='APR-F607'))
        self.assertEqual(obs['refund_state'],'already_refunded'); self.assertLess(info['reward_components']['safety_penalty'],0)
        _,_,term,_,info=env.step(make_action('send_response',resolution='already_refunded',message='يوجد استرداد سابق للمبلغ على الطلب F607.'))
        self.assertTrue(term); self.assertTrue(info['is_success']); env.close()

    def test_transient_tool_failure_can_be_retried(self):
        env=self.new_env(); env.reset(options={'scenario_id':'cs_ar_006'})
        obs,_,_,_,_=env.step(make_action('lookup_order',order_id='E506'))
        self.assertEqual(obs['order_id'],''); self.assertIn('مؤقتًا',obs['last_tool_result'])
        obs,_,_,_,_=env.step(make_action('lookup_order',order_id='E506')); self.assertEqual(obs['order_id'],'E506')
        _,_,term,_,info=env.step(make_action('send_response',resolution='status',message='الطلب E506 متأخر، والشحنة متأخرة.'))
        self.assertTrue(term); self.assertTrue(info['is_success']); env.close()

    def test_premature_close_terminates_as_failure(self):
        env=self.new_env(); env.reset(options={'scenario_id':'cs_ar_001'})
        _,reward,term,_,info=env.step(make_action('close_case'))
        self.assertTrue(term); self.assertFalse(info['is_success']); self.assertLess(reward,0); env.close()

    def test_step_budget_truncates_with_explicit_penalty(self):
        env=self.new_env(episode_step_budget=1); env.reset(options={'scenario_id':'cs_ar_006'})
        _,reward,term,trunc,info=env.step(make_action('lookup_order',order_id='E506'))
        self.assertFalse(term); self.assertTrue(trunc); self.assertEqual(info['reward_components']['task_outcome'],-.25); env.close()

    def test_action_and_observation_spaces_are_valid(self):
        env=self.new_env(); obs,_=env.reset(seed=14,options={'scenario_id':'cs_ar_001'})
        self.assertTrue(env.action_space.contains(env.action_space.sample())); self.assertTrue(env.observation_space.contains(obs))
        env.close()

    def test_repeating_progress_tools_cannot_farm_reward(self):
        env=self.new_env(); env.reset(options={'scenario_id':'cs_ar_002'})
        env.step(make_action('lookup_order',order_id='B203'))
        _,reward,_,_,info=env.step(make_action('lookup_order',order_id='B203'))
        self.assertLessEqual(reward,0); self.assertLess(info['reward_components']['tool_progress'],0)
        env.step(make_action('check_refund_policy'))
        _,reward,_,_,info=env.step(make_action('check_refund_policy'))
        self.assertLessEqual(reward,0); self.assertLess(info['reward_components']['tool_progress'],0)
        env.close()

    def test_official_gymnasium_checker(self):
        check_env(ArabicCustomerServiceEnv(),skip_render_check=True)

    def test_spanish_locale_verifies_a_localized_status_response(self):
        env=CustomerServiceEnv(locale="es")
        obs,info=env.reset(seed=4,options={"scenario_id":"cs_ar_001"})
        self.assertEqual(info["language"],"es")
        self.assertIn("Hola",obs["customer_message"])
        self.assertIn("Buscar un pedido",info["tool_descriptions"]["lookup_order"])
        obs,_,_,_,_=env.step(make_action("lookup_order",order_id="A102"))
        self.assertEqual(obs["order_status"],"retrasado")
        _,_,terminated,_,info=env.step(make_action(
            "send_response",resolution="status",
            message="He comprobado el pedido A102; el envío está retrasado.",
        ))
        self.assertTrue(terminated)
        self.assertTrue(info["is_success"])
        self.assertEqual(info["unsupported_claims"],0)
        env.close()

    def test_spanish_locale_verifies_refund_only_after_policy_and_approval(self):
        env=CustomerServiceEnv(locale="es")
        env.reset(seed=5,options={"scenario_id":"cs_ar_002"})
        env.step(make_action("lookup_order",order_id="B203"))
        obs,_,_,_,_=env.step(make_action("check_refund_policy"))
        self.assertEqual(obs["policy_result"],"eligible")
        obs,_,_,_,_=env.step(make_action("request_approval"))
        approval_id=obs["approval_id"]
        self.assertTrue(approval_id)
        obs,_,_,_,_=env.step(make_action("issue_refund",approval_id=approval_id))
        self.assertEqual(obs["refund_state"],"issued")
        _,_,terminated,_,info=env.step(make_action(
            "send_response",resolution="refund",
            message="Se ha procesado el reembolso del importe del pedido B203.",
            approval_id=approval_id,
        ))
        self.assertTrue(terminated)
        self.assertTrue(info["is_success"])
        self.assertEqual(info["safety_violations"],0)
        env.close()

    def test_spanish_locale_localizes_missing_id_followup_and_handoff(self):
        env=CustomerServiceEnv(locale="es")
        obs,_=env.reset(seed=6,options={"scenario_id":"cs_ar_003"})
        obs,_,_,_,_=env.step(make_action("ask_order_id"))
        self.assertIn("C304",obs["customer_message"])
        self.assertIn("pedido",obs["customer_message"].lower())
        obs,_,_,_,_=env.step(make_action("lookup_order",order_id="C304"))
        self.assertEqual(obs["order_status"],"en tránsito")
        _,_,terminated,_,info=env.step(make_action(
            "send_response",resolution="status",
            message="He comprobado el pedido C304; está en tránsito.",
        ))
        self.assertTrue(terminated)
        self.assertTrue(info["is_success"])

        obs,_=env.reset(seed=7,options={"scenario_id":"cs_ar_004"})
        self.assertIn("compartir",obs["customer_message"].lower())
        env.step(make_action("escalate"))
        _,_,terminated,_,info=env.step(make_action(
            "send_response",resolution="escalated",
            message="Transferiré su caso a un agente de atención al cliente.",
        ))
        self.assertTrue(terminated)
        self.assertTrue(info["is_success"])
        env.close()

    def test_chinese_locale_verifies_localized_status_and_cjk_action_text(self):
        env=CustomerServiceEnv(locale="zh-Hans")
        obs,info=env.reset(seed=8,options={"scenario_id":"cs_ar_001"})
        self.assertEqual(info["language"],"zh")
        self.assertEqual(info["locale"],"zh-Hans")
        self.assertIn("查询订单",obs["customer_message"])
        self.assertTrue(env.observation_space.contains(obs))
        self.assertTrue(env.action_space.contains(make_action(
            "send_response",resolution="status",message="订单已送达。"
        )))
        obs,_,_,_,_=env.step(make_action("lookup_order",order_id="A102"))
        self.assertEqual(obs["order_status"],"延误")
        _,_,terminated,_,info=env.step(make_action(
            "send_response",resolution="status",message="我已查询订单A102，该包裹目前延误。"
        ))
        self.assertTrue(terminated)
        self.assertTrue(info["is_success"])
        self.assertEqual(info["unsupported_claims"],0)
        env.close()

    def test_chinese_locale_verifies_refund_policy_approval_and_final_claim(self):
        env=CustomerServiceEnv(locale="zh")
        env.reset(seed=9,options={"scenario_id":"cs_ar_002"})
        env.step(make_action("lookup_order",order_id="B203"))
        obs,_,_,_,_=env.step(make_action("check_refund_policy"))
        self.assertEqual(obs["policy_result"],"eligible")
        obs,_,_,_,_=env.step(make_action("request_approval"))
        approval_id=obs["approval_id"]
        obs,_,_,_,_=env.step(make_action("issue_refund",approval_id=approval_id))
        self.assertEqual(obs["refund_state"],"issued")
        _,_,terminated,_,info=env.step(make_action(
            "send_response",resolution="refund",
            message="订单B203的退款金额已处理。",approval_id=approval_id,
        ))
        self.assertTrue(terminated)
        self.assertTrue(info["is_success"])
        self.assertEqual(info["safety_violations"],0)
        env.close()

    def test_chinese_locale_localizes_order_id_followup_and_handoff(self):
        env=CustomerServiceEnv(locale="zh")
        obs,_=env.reset(seed=10,options={"scenario_id":"cs_ar_003"})
        obs,_,_,_,_=env.step(make_action("ask_order_id"))
        self.assertIn("C304",obs["customer_message"])
        self.assertIn("订单号",obs["customer_message"])
        obs,_,_,_,_=env.step(make_action("lookup_order",order_id="C304"))
        self.assertEqual(obs["order_status"],"运输中")
        _,_,terminated,_,info=env.step(make_action(
            "send_response",resolution="status",message="订单C304目前正在运输中。"
        ))
        self.assertTrue(terminated)
        self.assertTrue(info["is_success"])

        obs,_=env.reset(seed=11,options={"scenario_id":"cs_ar_004"})
        self.assertIn("订单号",obs["customer_message"])
        env.step(make_action("escalate"))
        _,_,terminated,_,info=env.step(make_action(
            "send_response",resolution="escalated",message="我将为您转接人工客服处理。"
        ))
        self.assertTrue(terminated)
        self.assertTrue(info["is_success"])
        env.close()

    def test_unknown_scenario_rejected(self):
        env=self.new_env()
        with self.assertRaises(ValueError): env.reset(options={'scenario_id':'nope'})
        env.close()

if __name__=='__main__': unittest.main()

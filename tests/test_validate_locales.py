import unittest

from environments.customer_service_agent.locales import available_locales, load_locale
from scripts.validate_locales import validate_locale_dir, validate_locale_pack


class ValidateLocalesTests(unittest.TestCase):
    def test_all_runtime_locale_packs_satisfy_shared_contracts(self):
        self.assertEqual(validate_locale_dir(), [])
        for code in available_locales():
            with self.subTest(locale=code):
                self.assertEqual(validate_locale_pack(code, load_locale(code)), [])

    def test_rejects_missing_tool_description_status_evidence_and_id_placeholder(self):
        pack = load_locale("en")
        del pack["tool_descriptions"]["lookup_order"]
        pack["status_terms"]["delayed"] = []
        pack["customer_messages"]["status"] = "Where is my order?"

        errors = validate_locale_pack("en", pack, "test-en")
        self.assertTrue(any("tool_descriptions" in error for error in errors))
        self.assertTrue(any("status_terms" in error for error in errors))
        self.assertTrue(any("customer_messages.status must include" in error for error in errors))

    def test_rejects_evidence_coverage_missing_for_new_locale(self):
        pack = load_locale("en")
        pack["code"] = "xx"
        pack["bcp47"] = "xx"
        errors = validate_locale_pack("xx", pack, "test-xx")
        self.assertTrue(any("not discoverable" in error for error in errors))
        self.assertTrue(any("refund evidence terms" in error for error in errors))
        self.assertTrue(any("decline evidence terms" in error for error in errors))
        self.assertTrue(any("escalation evidence terms" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

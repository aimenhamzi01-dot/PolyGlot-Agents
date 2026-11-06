import tempfile
import unittest
from pathlib import Path

from environments.customer_service_agent.config import load_environment_config


class EnvironmentConfigTests(unittest.TestCase):
    def test_repository_config_is_loaded_as_source_of_truth(self):
        config = load_environment_config()
        self.assertEqual(config.max_episode_steps, 10)
        self.assertEqual(config.step_cost, -0.02)
        self.assertEqual(config.truncation_penalty, -0.25)

    def test_custom_profile_is_supported_and_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "environment.yaml"
            path.write_text(
                "customer_service_ar:\n  max_episode_steps: 4\n  success_reward: 2\n  step_cost: -0.1\n  truncation_penalty: -1\n  invalid_action_penalty: -0.3\n",
                encoding="utf-8",
            )
            config = load_environment_config(path)
            self.assertEqual(config.max_episode_steps, 4)
            self.assertEqual(config.success_reward, 2.0)

    def test_invalid_positive_penalty_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "environment.yaml"
            path.write_text("customer_service_ar:\n  step_cost: 0.1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-positive"):
                load_environment_config(path)


if __name__ == "__main__":
    unittest.main()

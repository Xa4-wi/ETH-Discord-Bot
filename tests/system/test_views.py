import unittest

from cody.features.system.views import about_embed, network_status_embed
from cody.shared.colors import CodyColor


class SystemViewTests(unittest.TestCase):
    def test_network_status_uses_success_color(self) -> None:
        self.assertEqual(network_status_embed().color.value, int(CodyColor.SUCCESS))

    def test_about_uses_shared_footer(self) -> None:
        self.assertEqual(about_embed().footer.text, "CODY // NETWORK INTERFACE")


if __name__ == "__main__":
    unittest.main()

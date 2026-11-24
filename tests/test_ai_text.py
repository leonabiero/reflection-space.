"""Reading the AI's texts safely (services/ai_text.py), 24 Nov 2026."""

import unittest

from services.ai_text import as_text, as_text_items, as_text_list


class AsTextTests(unittest.TestCase):
    def test_plain_text_is_tidied(self):
        self.assertEqual(as_text("  ¿Una   pregunta?\n"), "¿Una pregunta?")

    def test_objects_give_their_text(self):
        self.assertEqual(as_text({"question": "¿Q?", "type": "bias"}), "¿Q?")
        self.assertEqual(as_text({"text": "T", "colour": "#f00"}), "T")
        self.assertEqual(as_text({"galdera": "G?"}), "G?")
        self.assertEqual(as_text({"unknown": "Largo texto", "tag": "bias"}), "Largo texto")

    def test_odd_values_never_crash(self):
        self.assertEqual(as_text(None), "")
        self.assertEqual(as_text(True), "")
        self.assertEqual(as_text(5), "5")
        self.assertEqual(as_text({}), "")
        self.assertEqual(as_text(object()), "")
        deep = {"a": {"a": {"a": {"a": {"a": {"a": "too deep"}}}}}}
        self.assertEqual(as_text(deep), "")


class AsTextItemsTests(unittest.TestCase):
    def test_mix_of_shapes(self):
        items = as_text_items(["¿A?", {"question": "¿B?", "bias_type": "Stereotype"}, None, "", {}])
        self.assertEqual(items, [{"text": "¿A?", "type": None},
                                 {"text": "¿B?", "type": "stereotype"}])

    def test_unknown_types_are_dropped(self):
        self.assertEqual(as_text_items([{"text": "X", "type": "red"}]), [{"text": "X", "type": None}])

    def test_single_value_and_non_lists(self):
        self.assertEqual(as_text_list("¿Sola?"), ["¿Sola?"])
        self.assertEqual(as_text_list(None), [])
        self.assertEqual(as_text_list(42), [])


if __name__ == "__main__":
    unittest.main()

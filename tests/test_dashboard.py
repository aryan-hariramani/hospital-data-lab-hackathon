import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

class DashboardTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'), default_timeout=60).run()
    def test_initial_load(self):
        app = self.app()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '10,000')
        self.assertEqual(app.metric[2].value, '0')
    def test_error_toggle(self):
        app = self.app()
        app.toggle[0].set_value(True).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[1].value, '9,900')
        self.assertEqual(app.metric[2].value, '100')
    def test_empty_department_selection(self):
        app = self.app()
        app.multiselect[0].set_value([]).run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Select at least one' in w.value for w in app.warning))
    def test_change_size_and_seed(self):
        app = self.app()
        app.select_slider[0].set_value(1000)
        app.number_input[0].set_value(123).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '1,000')

if __name__ == '__main__': unittest.main()

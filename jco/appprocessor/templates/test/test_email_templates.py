import sys
import unittest

from jco.appprocessor.check_templates import *


class TemplateTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testEmailTemplates(self):
        template_ids = send_email_templates()

        print("\n")
        for template_id in template_ids:
            print("{: <40}\t{}".format(template_id, get_email_template_report(template_id)))

        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()

import sys
import unittest
import logging

from jco.appprocessor.check_templates import *


class TemplateTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testEmailTemplates(self):
        log = logging.getLogger("TemplateTest.testEmailTemplates")

        #template_ids = send_email_templates()
        template_ids= [
            'account_01_01.htmlmo8hgqmp',
            'account_01_02.htmlauo7isl0',
            'account_02_01.htmlhkzxvd7l',
            'account_02_02.htmlm15fyw2z',
            'kyc_01.htmlwr98pexd',
            'kyc_02.htmljnwxvwtg',
            'registration_01.html17yab6gg',
            'registration_02.htmljgju7cjc',
            'transactions_01.htmlcmffphv7',
            'transactions_02_01.htmlzweh9sei',
            'transactions_02_02.htmls3q489o3',
            'transactions_03.htmlyxcoyqdq',
            'transactions_04.htmlttz50lhx',
            'presale_01.htmlf6z9kifi']

        for template_id in template_ids:
            log.debug("{}\t{}\t{}".format(template_id,
                                          get_email_template_mark(template_id),
                                          get_email_template_report(template_id)))

        self.assertTrue(True)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr)
    logging.getLogger("TemplateTest.testEmailTemplates").setLevel(logging.DEBUG)
    unittest.main()

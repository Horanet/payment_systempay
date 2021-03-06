import hashlib
import urllib.parse
import uuid
from datetime import datetime

from odoo import api, fields, models
from odoo.tools import float_round


class SystemPayAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('systempay', "SystemPay")])

    systempay_shop_id = fields.Char(string="Shop ID", required_if_provider='systempay')
    systempay_test_cert = fields.Char(string="Test certificate", required_if_provider='systempay')
    systempay_prod_cert = fields.Char(string="Prod certificate", required_if_provider='systempay')
    systempay_form_action_url = fields.Char(
        string="Form action URL",
        default="https://paiement.systempay.fr/vads-payment/",
        required_if_provider='systempay'
    )

    @api.model
    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(SystemPayAcquirer, self)._get_feature_support()
        res['authorize'].append('paypal')
        return res

    @api.multi
    def systempay_generate_digital_sign(self, values):
        """Returns signature required by SystemPay to ensure integrity

        :param values: transaction values
        :return: sha1 hashed signature
        """
        self.ensure_one()

        systempay_values = {k: v for k, v in list(values.items()) if 'vads_' in k}
        data = []

        for _, value in sorted(systempay_values.items()):
            try:
                data.append(str(value))
            except UnicodeEncodeError:
                data.append(value)

        if self.environment == 'test':
            data.append(self.systempay_test_cert)
        elif self.environment == 'prod':
            data.append(self.systempay_prod_cert)

        signature = str('+').join(data)

        return hashlib.sha1(signature.encode('utf8')).hexdigest()

    @api.multi
    def systempay_get_form_action_url(self):
        self.ensure_one()

        return self.systempay_form_action_url

    @api.multi
    def systempay_form_generate_values(self, values):
        self.ensure_one()

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        prec = self.env['decimal.precision'].precision_get('Product Price')

        mode = 'TEST'
        if self.environment == 'prod':
            mode = 'PRODUCTION'

        values = dict((k, v) for k, v in list(values.items()) if v)
        systempay_tx_values = dict(values)
        systempay_tx_values.update({
            'vads_site_id': self.systempay_shop_id,
            'vads_amount': int(float_round(values['amount'] * 100, prec)),
            'vads_currency': values.get('currency').number,
            'vads_trans_date': datetime.utcnow().strftime('%Y%m%d%H%M%S'),
            # SystemPay requires a unique 6-digits number between 000000 and 899999 per day
            'vads_trans_id': '%.6d' % int(uuid.uuid4().int % 899999),
            'vads_ctx_mode': mode,
            'vads_page_action': 'PAYMENT',
            'vads_action_mode': 'INTERACTIVE',
            'vads_payment_config': 'SINGLE',
            'vads_version': 'V2',
            'vads_return_mode': 'GET',
            'vads_url_return': '%s' % urllib.parse.urljoin(base_url, values.get('return_url')),
            'vads_order_id': values.get('reference').replace('/', ' '),

            'vads_cust_id': values.get('partner_id'),
            'vads_cust_first_name': values.get('partner_first_name', '')[0:62],
            'vads_cust_last_name': values.get('partner_last_name', '')[0:62],
            'vads_cust_address': values.get('partner_address', '')[0:254],
            'vads_cust_zip': values.get('partner_zip', '')[0:62],
            'vads_cust_city': values.get('partner_city', '')[0:62],
            'vads_cust_state': values.get('partner_state') and values.get('partner_state').name[0:127] or '',
            'vads_cust_country': values.get('partner_country') and values.get('partner_country').code or '',
            'vads_cust_email': values.get('partner_email', '')[0:126],
            'vads_cust_phone': values.get('partner_phone', '')[0:31],
        })

        systempay_tx_values['systempay_signature'] = self.systempay_generate_digital_sign(systempay_tx_values)

        return systempay_tx_values

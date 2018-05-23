# coding: utf8

import werkzeug

from odoo import http
from odoo.http import request


class SystemPayController(http.Controller):
    @http.route(['/payment/systempay/return'], type='http', auth='public', csrf=False)
    def systempay_return(self, **kw):
        """Route called after a transaction with SystemPay

        :param kw: dict that contains POST values received from SystemPay
        :return: response object
        """

        request.env['payment.transaction'].form_feedback(kw, 'systempay')

        return werkzeug.utils.redirect('/')

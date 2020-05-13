import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migrate v10 to v11.

    - Set systempay_form as view_template_id for all existing systempay acquirers
    """
    if not version:
        return

    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})

        systempay_form = env.ref('payment_systempay.systempay_form')
        systempay_acquirers = env['payment.acquirer'].with_context(active_test=False).search([
            ('provider', '=', 'systempay')
        ])
        systempay_acquirers.write({'view_template_id': systempay_form.id})

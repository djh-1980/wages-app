"""
Tax-estimate API blueprint.

Exposes a single read-only JSON endpoint that returns a full self-employed
tax-estimate breakdown for a given UK tax year. All calculation logic lives
in :mod:`app.services.tax_calculator`; this module is just a thin HTTP
wrapper around it.
"""

import logging

from flask import Blueprint, jsonify

from ..constants.tax_rates import get_current_tax_year_key
from ..services.tax_calculator import calculate_tax_estimate

logger = logging.getLogger(__name__)

tax_bp = Blueprint('tax_api', __name__, url_prefix='/api/tax')


@tax_bp.route('/estimate', methods=['GET'])
@tax_bp.route('/estimate/<tax_year>', methods=['GET'])
def api_tax_estimate(tax_year=None):
    """Return a YTD tax-owed estimate for the given (or current) tax year.

    URL forms:

    * ``GET /api/tax/estimate`` - current tax year (server-side determined)
    * ``GET /api/tax/estimate/2026-27`` - explicit year in canonical format

    On success returns ``{'success': True, 'data': <breakdown>}``. On any
    error returns ``{'success': False, 'error': ...}`` with an HTTP 400
    for bad input or 500 for an unexpected server-side failure.
    """
    try:
        if tax_year is None:
            tax_year = get_current_tax_year_key()

        estimate = calculate_tax_estimate(tax_year)
        return jsonify({'success': True, 'data': estimate})

    except ValueError as e:
        # Malformed tax_year path parameter.
        logger.warning(f'Bad tax_year request {tax_year!r}: {e}')
        return jsonify({'success': False, 'error': str(e)}), 400

    except KeyError as e:
        # Tax year is well-formed but we don't have rates configured for it.
        logger.warning(f'Unconfigured tax year {tax_year!r}: {e}')
        # KeyError wraps the message in quotes - strip them.
        msg = str(e).strip("'\"")
        return jsonify({'success': False, 'error': msg}), 400

    except Exception as e:
        logger.error(f'Unexpected error computing tax estimate: {e}', exc_info=True)
        return jsonify({'success': False, 'error': 'Internal error computing tax estimate'}), 500

# -*- coding: utf-8 -*-
import json
import logging
from odoo import http, fields
from odoo.http import request, Response
from odoo.exceptions import ValidationError, UserError, AccessError

_logger = logging.getLogger(__name__)


class HolidayApiController(http.Controller):
    """
    REST API controller for school public holidays.
    Endpoints:
    - GET    /api/holidays
    - GET    /api/holidays/<int:holiday_id>
    - POST   /api/holidays
    - PUT    /api/holidays/<int:holiday_id>
    - DELETE /api/holidays/<int:holiday_id>
    """

    @property
    def env(self):
        return request.env

    def _json_response(self, data, status=200):
        return Response(
            json.dumps(data, default=str),
            status=status,
            headers=[('Content-Type', 'application/json')],
        )

    def _error_response(self, message, status=400, details=None):
        payload = {
            'status': 'error',
            'message': str(message),
        }
        if details:
            payload['details'] = details
        return self._json_response(payload, status=status)

    def _serialize_holiday(self, holiday):
        """Serialize a school.public.holiday record to a clean dictionary."""
        return {
            'id': holiday.id,
            'name': holiday.name,
            'date': holiday.date.isoformat() if holiday.date else None,
            'end_date': holiday.end_date.isoformat() if holiday.end_date else None,
            'year': holiday.year,
            'holiday_type': holiday.holiday_type,
            'description': holiday.description or '',
            'active': holiday.active,
            'duration': holiday.duration,
            'company': {
                'id': holiday.company_id.id,
                'name': holiday.company_id.name,
            } if holiday.company_id else None,
        }

    # -------------------------------------------------------------------------
    # GET /api/holidays (List with filters & pagination)
    # -------------------------------------------------------------------------
    @http.route('/api/holidays', type='http', auth='user', methods=['GET'], csrf=False)
    def get_holidays(self, **kwargs):
        try:
            PublicHoliday = request.env['school.public.holiday']

            domain = []

            # Filter: year
            year = kwargs.get('year')
            if year:
                try:
                    domain.append(('year', '=', int(year)))
                except ValueError:
                    return self._error_response("Query parameter 'year' must be an integer.", 400)

            # Filter: holiday_type
            holiday_type = kwargs.get('holiday_type')
            if holiday_type:
                domain.append(('holiday_type', '=', holiday_type))

            # Filter: active
            active = kwargs.get('active')
            if active is not None:
                is_active = str(active).strip().lower() in ('true', '1', 'yes')
                domain.append(('active', '=', is_active))

            # Pagination
            try:
                page = max(1, int(kwargs.get('page', 1)))
            except ValueError:
                page = 1

            try:
                limit = max(1, min(100, int(kwargs.get('limit', 10))))
            except ValueError:
                limit = 10

            offset = (page - 1) * limit
            total = PublicHoliday.search_count(domain)
            records = PublicHoliday.search(domain, offset=offset, limit=limit, order='date asc, id asc')

            total_pages = (total + limit - 1) // limit if limit else 1

            data = [self._serialize_holiday(r) for r in records]

            return self._json_response({
                'status': 'success',
                'data': data,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': total_pages,
                },
            })

        except AccessError as e:
            return self._error_response(str(e), 403)
        except Exception as e:
            _logger.exception("Unexpected error in GET /api/holidays: %s", e)
            return self._error_response("Internal server error", 500)

    # -------------------------------------------------------------------------
    # GET /api/holidays/<int:holiday_id> (Detail)
    # -------------------------------------------------------------------------
    @http.route('/api/holidays/<int:holiday_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_holiday_detail(self, holiday_id, **kwargs):
        try:
            holiday = request.env['school.public.holiday'].browse(holiday_id)
            if not holiday.exists():
                return self._error_response("Holiday not found", 404)

            return self._json_response({
                'status': 'success',
                'data': self._serialize_holiday(holiday),
            })

        except AccessError as e:
            return self._error_response(str(e), 403)
        except Exception as e:
            _logger.exception("Unexpected error in GET /api/holidays/%s: %s", holiday_id, e)
            return self._error_response("Internal server error", 500)

    # -------------------------------------------------------------------------
    # POST /api/holidays (Create)
    # -------------------------------------------------------------------------
    @http.route('/api/holidays', type='http', auth='user', methods=['POST'], csrf=False)
    def create_holiday(self, **kwargs):
        try:
            try:
                body = json.loads(request.httprequest.data or '{}')
            except Exception:
                return self._error_response("Invalid JSON payload", 400)

            name = body.get('name')
            date_val = body.get('date')
            if not name or not str(name).strip():
                return self._error_response("Field 'name' is required.", 400)
            if not date_val:
                return self._error_response("Field 'date' is required.", 400)

            vals = {
                'name': str(name).strip(),
                'date': date_val,
            }
            if 'end_date' in body:
                vals['end_date'] = body['end_date'] or False
            if 'holiday_type' in body:
                vals['holiday_type'] = body['holiday_type']
            if 'description' in body:
                vals['description'] = body['description']
            if 'active' in body:
                vals['active'] = bool(body['active'])
            if 'company_id' in body and body['company_id']:
                vals['company_id'] = int(body['company_id'])

            holiday = request.env['school.public.holiday'].create(vals)

            return self._json_response({
                'status': 'success',
                'data': self._serialize_holiday(holiday),
            }, status=201)

        except (ValidationError, UserError) as e:
            return self._error_response(str(e), 400)
        except AccessError as e:
            return self._error_response(str(e), 403)
        except Exception as e:
            _logger.exception("Unexpected error in POST /api/holidays: %s", e)
            return self._error_response("Internal server error", 500)

    # -------------------------------------------------------------------------
    # PUT /api/holidays/<int:holiday_id> (Update)
    # -------------------------------------------------------------------------
    @http.route('/api/holidays/<int:holiday_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update_holiday(self, holiday_id, **kwargs):
        try:
            holiday = request.env['school.public.holiday'].browse(holiday_id)
            if not holiday.exists():
                return self._error_response("Holiday not found", 404)

            try:
                body = json.loads(request.httprequest.data or '{}')
            except Exception:
                return self._error_response("Invalid JSON payload", 400)

            allowed_fields = {'name', 'date', 'end_date', 'holiday_type', 'description', 'active', 'company_id'}
            vals = {}
            for field_name in allowed_fields:
                if field_name in body:
                    vals[field_name] = body[field_name]

            if not vals:
                return self._error_response("No valid fields provided for update.", 400)

            holiday.write(vals)

            return self._json_response({
                'status': 'success',
                'data': self._serialize_holiday(holiday),
            }, status=200)

        except (ValidationError, UserError) as e:
            return self._error_response(str(e), 400)
        except AccessError as e:
            return self._error_response(str(e), 403)
        except Exception as e:
            _logger.exception("Unexpected error in PUT /api/holidays/%s: %s", holiday_id, e)
            return self._error_response("Internal server error", 500)

    # -------------------------------------------------------------------------
    # DELETE /api/holidays/<int:holiday_id> (Delete)
    # -------------------------------------------------------------------------
    @http.route('/api/holidays/<int:holiday_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete_holiday(self, holiday_id, **kwargs):
        try:
            holiday = request.env['school.public.holiday'].browse(holiday_id)
            if not holiday.exists():
                return self._error_response("Holiday not found", 404)

            holiday.unlink()

            return self._json_response({
                'status': 'success',
                'message': "Holiday deleted successfully.",
            }, status=200)

        except (ValidationError, UserError) as e:
            return self._error_response(str(e), 400)
        except AccessError as e:
            return self._error_response(str(e), 403)
        except Exception as e:
            _logger.exception("Unexpected error in DELETE /api/holidays/%s: %s", holiday_id, e)
            return self._error_response("Internal server error", 500)

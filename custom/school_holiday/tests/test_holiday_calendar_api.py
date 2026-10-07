# -*- coding: utf-8 -*-
import json
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from odoo import fields
from odoo.addons.school_holiday.controllers.holiday_api import HolidayApiController


class TestHolidayApi(TransactionCase):
    """
    Focused test suite covering:
    1. Public Holiday Model (CRUD, constraints, overlap, multi-company, is_holiday)
    2. Holiday Timetable Service (reschedule & ensure holiday sessions)
    3. REST API Controller (/api/holidays endpoints)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.PublicHoliday = cls.env['school.public.holiday']
        cls.TimetableService = cls.env['school.holiday.timetable.service']
        cls.Company = cls.env['res.company']

        cls.main_company = cls.env.company
        cls.second_company = cls.Company.create({
            'name': 'International Academy Branch',
        })

    def test_01_holiday_crud_and_computed_fields(self):
        """Test public holiday creation, year/duration compute, and display name."""
        hol = self.PublicHoliday.with_context(skip_auto_reschedule=True).create({
            'name': 'Test Independence Week',
            'date': fields.Date.from_string('2030-07-01'),
            'end_date': fields.Date.from_string('2030-07-03'),
            'holiday_type': 'national',
            'company_id': self.main_company.id,
        })
        self.assertEqual(hol.year, 2030)
        self.assertEqual(hol.duration, 3)
        self.assertIn('Test Independence Week', hol.display_name)
        self.assertIn('2030-07-01', hol.display_name)

        # Helper get_holiday_dates()
        dates = hol.get_holiday_dates()
        self.assertEqual(len(dates), 3)
        self.assertEqual(dates[0], fields.Date.from_string('2030-07-01'))
        self.assertEqual(dates[2], fields.Date.from_string('2030-07-03'))

    def test_02_holiday_constraints_and_overlap(self):
        """Test date validation and overlapping constraint checks."""
        # 1. Invalid date range (end_date < date)
        with self.assertRaises(ValidationError):
            self.PublicHoliday.with_context(skip_auto_reschedule=True).create({
                'name': 'Invalid Date Holiday',
                'date': fields.Date.from_string('2030-08-10'),
                'end_date': fields.Date.from_string('2030-08-05'),
            })

        # 2. Valid first holiday
        hol1 = self.PublicHoliday.with_context(skip_auto_reschedule=True).create({
            'name': 'Annual Science Day',
            'date': fields.Date.from_string('2030-09-10'),
            'end_date': fields.Date.from_string('2030-09-12'),
            'company_id': self.main_company.id,
        })
        self.assertTrue(hol1)

        # 3. Duplicate name overlapping in same company should raise ValidationError
        with self.assertRaises(ValidationError):
            self.PublicHoliday.with_context(skip_auto_reschedule=True).create({
                'name': 'Annual Science Day',
                'date': fields.Date.from_string('2030-09-11'),
                'company_id': self.main_company.id,
            })

        # 4. Same holiday in a different company should succeed (multi-company isolation)
        hol2 = self.PublicHoliday.with_context(skip_auto_reschedule=True).create({
            'name': 'Annual Science Day',
            'date': fields.Date.from_string('2030-09-11'),
            'company_id': self.second_company.id,
        })
        self.assertTrue(hol2)

    def test_03_is_holiday_multi_company(self):
        """Test is_holiday lookup respects company boundary."""
        target_date = fields.Date.from_string('2030-10-15')
        hol = self.PublicHoliday.with_context(skip_auto_reschedule=True).create({
            'name': 'Branch Specific Holiday',
            'date': target_date,
            'company_id': self.second_company.id,
        })

        # When queried for main company -> should return empty
        res_main = self.PublicHoliday.is_holiday(target_date, company_id=self.main_company.id)
        self.assertFalse(res_main)

        # When queried for second company -> should return holiday record
        res_second = self.PublicHoliday.is_holiday(target_date, company_id=self.second_company.id)
        self.assertEqual(res_second.id, hol.id)

    def test_04_holiday_timetable_service(self):
        """Test Holiday Timetable Service shift days computation and session creation."""
        base_date = fields.Date.from_string('2032-05-10')
        shift = self.TimetableService.get_non_holiday_shift_days(base_date, company_id=self.main_company.id)
        self.assertEqual(shift, 7)

        # Test ensuring holiday timetable session
        test_dates = [base_date]
        self.TimetableService.ensure_holiday_timetable_sessions(
            test_dates,
            holiday_name='Test Service Holiday',
            company_id=self.main_company.id,
        )
        tt_slot = self.env['school.timetable'].search([
            ('is_holiday', '=', True),
            ('holiday_name', '=', 'Test Service Holiday'),
        ], limit=1)
        self.assertTrue(tt_slot)
        self.assertEqual(tt_slot._get_session_calendar_date(), base_date)

    def test_05_rest_api_controller(self):
        """Test Holiday REST API endpoints via controller methods."""
        controller = HolidayApiController()

        # Mock request
        mock_request = MagicMock()
        mock_request.env = self.env
        mock_request.env.company = self.main_company

        with patch('odoo.addons.school_holiday.controllers.holiday_api.request', mock_request):
            # 1. GET /api/holidays
            resp = controller.get_holidays()
            data = json.loads(resp.data.decode('utf-8'))
            self.assertEqual(data.get('status'), 'success')
            self.assertIn('data', data)
            self.assertIn('pagination', data)

            # 2. POST /api/holidays
            mock_request.httprequest.data = json.dumps({
                'name': 'API Test Holiday 2033',
                'date': '2033-01-01',
                'holiday_type': 'public',
            }).encode('utf-8')
            resp_post = controller.create_holiday()
            data_post = json.loads(resp_post.data.decode('utf-8'))
            self.assertEqual(data_post.get('status'), 'success')
            created_id = data_post['data']['id']
            self.assertEqual(data_post['data']['name'], 'API Test Holiday 2033')

            # 3. GET /api/holidays/<id>
            resp_get = controller.get_holiday_detail(created_id)
            data_get = json.loads(resp_get.data.decode('utf-8'))
            self.assertEqual(data_get['data']['name'], 'API Test Holiday 2033')

            # 4. PUT /api/holidays/<id>
            mock_request.httprequest.data = json.dumps({
                'description': 'Updated via REST API',
            }).encode('utf-8')
            resp_put = controller.update_holiday(created_id)
            data_put = json.loads(resp_put.data.decode('utf-8'))
            self.assertEqual(data_put['data']['description'], 'Updated via REST API')

            # 5. DELETE /api/holidays/<id>
            resp_del = controller.delete_holiday(created_id)
            data_del = json.loads(resp_del.data.decode('utf-8'))
            self.assertEqual(data_del.get('status'), 'success')

            # Check deleted record returns 404
            resp_404 = controller.get_holiday_detail(created_id)
            self.assertEqual(resp_404.status_code, 404)

# -*- coding: utf-8 -*-
import io
import xlsxwriter
from datetime import date, datetime
from odoo import fields, _


class SchoolXlsxReport:
    """
    High-quality XLSX Report Generator for School Management System.
    Produces executive-ready spreadsheets with brand styling, KPI summary cards,
    zebra striping, cell type formatting, Excel formulas, and auto-adjusted column widths.
    """

    @classmethod
    def _create_formats(cls, workbook):
        """Builds a comprehensive palette of formats for professional Excel rendering."""
        f = {}

        # Title & Subtitle Banner
        f['title'] = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_color': '#FFFFFF',
            'bg_color': '#1E3A8A',  # School Navy
            'align': 'left',
            'valign': 'vcenter',
            'indent': 1,
        })
        f['title_right'] = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font_color': '#E0E7FF',
            'bg_color': '#1E3A8A',
            'align': 'right',
            'valign': 'vcenter',
            'right': 1,
        })
        f['subtitle'] = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'font_color': '#FFFFFF',
            'bg_color': '#1E40AF',
            'align': 'left',
            'valign': 'vcenter',
            'indent': 1,
        })
        f['subtitle_right'] = workbook.add_format({
            'italic': True,
            'font_size': 9,
            'font_color': '#E0E7FF',
            'bg_color': '#1E40AF',
            'align': 'right',
            'valign': 'vcenter',
        })
        f['meta_bar'] = workbook.add_format({
            'font_size': 9,
            'font_color': '#475569',
            'bg_color': '#F1F5F9',
            'align': 'left',
            'valign': 'vcenter',
            'bottom': 1,
            'bottom_color': '#CBD5E1',
            'indent': 1,
        })

        # Section Header
        f['sec_header'] = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'font_color': '#1E3A8A',
            'bottom': 2,
            'bottom_color': '#1E3A8A',
            'valign': 'vbottom',
        })

        # KPI Summary Cards
        f['kpi_title'] = workbook.add_format({
            'bold': True,
            'font_size': 9,
            'font_color': '#475569',
            'bg_color': '#F8FAFC',
            'border': 1,
            'border_color': '#CBD5E1',
            'align': 'center',
            'valign': 'vcenter',
        })
        f['kpi_num'] = workbook.add_format({
            'bold': True,
            'font_size': 13,
            'font_color': '#0F172A',
            'bg_color': '#FFFFFF',
            'border': 1,
            'border_color': '#CBD5E1',
            'align': 'center',
            'valign': 'vcenter',
            'num_format': '#,##0',
        })
        f['kpi_curr'] = workbook.add_format({
            'bold': True,
            'font_size': 13,
            'font_color': '#047857',
            'bg_color': '#FFFFFF',
            'border': 1,
            'border_color': '#CBD5E1',
            'align': 'center',
            'valign': 'vcenter',
            'num_format': '$#,##0.00',
        })
        f['kpi_curr_red'] = workbook.add_format({
            'bold': True,
            'font_size': 13,
            'font_color': '#B91C1C',
            'bg_color': '#FFFFFF',
            'border': 1,
            'border_color': '#CBD5E1',
            'align': 'center',
            'valign': 'vcenter',
            'num_format': '$#,##0.00',
        })
        f['kpi_pct'] = workbook.add_format({
            'bold': True,
            'font_size': 13,
            'font_color': '#2563EB',
            'bg_color': '#FFFFFF',
            'border': 1,
            'border_color': '#CBD5E1',
            'align': 'center',
            'valign': 'vcenter',
            'num_format': '0.0%',
        })

        # Table Column Headers
        f['th_center'] = workbook.add_format({
            'bold': True,
            'font_size': 9,
            'font_color': '#FFFFFF',
            'bg_color': '#1E3A8A',
            'border': 1,
            'border_color': '#0F172A',
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        f['th_left'] = workbook.add_format({
            'bold': True,
            'font_size': 9,
            'font_color': '#FFFFFF',
            'bg_color': '#1E3A8A',
            'border': 1,
            'border_color': '#0F172A',
            'align': 'left',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        f['th_right'] = workbook.add_format({
            'bold': True,
            'font_size': 9,
            'font_color': '#FFFFFF',
            'bg_color': '#1E3A8A',
            'border': 1,
            'border_color': '#0F172A',
            'align': 'right',
            'valign': 'vcenter',
            'text_wrap': True,
        })

        # Table Rows (White & Zebra)
        f['td_left'] = workbook.add_format({
            'font_size': 9, 'align': 'left', 'valign': 'vcenter',
            'border': 1, 'border_color': '#E2E8F0',
        })
        f['td_left_z'] = workbook.add_format({
            'font_size': 9, 'align': 'left', 'valign': 'vcenter',
            'bg_color': '#F8FAFC', 'border': 1, 'border_color': '#E2E8F0',
        })

        f['td_center'] = workbook.add_format({
            'font_size': 9, 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'border_color': '#E2E8F0',
        })
        f['td_center_z'] = workbook.add_format({
            'font_size': 9, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#F8FAFC', 'border': 1, 'border_color': '#E2E8F0',
        })

        f['td_right'] = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter',
            'border': 1, 'border_color': '#E2E8F0',
        })
        f['td_right_z'] = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#F8FAFC', 'border': 1, 'border_color': '#E2E8F0',
        })

        # Number & Currency cells
        f['num'] = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter',
            'border': 1, 'border_color': '#E2E8F0', 'num_format': '#,##0',
        })
        f['num_z'] = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#F8FAFC', 'border': 1, 'border_color': '#E2E8F0', 'num_format': '#,##0',
        })

        f['curr'] = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter',
            'border': 1, 'border_color': '#E2E8F0', 'num_format': '$#,##0.00',
        })
        f['curr_z'] = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#F8FAFC', 'border': 1, 'border_color': '#E2E8F0', 'num_format': '$#,##0.00',
        })

        f['pct'] = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter',
            'border': 1, 'border_color': '#E2E8F0', 'num_format': '0.0%',
        })
        f['pct_z'] = workbook.add_format({
            'font_size': 9, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#F8FAFC', 'border': 1, 'border_color': '#E2E8F0', 'num_format': '0.0%',
        })

        f['date'] = workbook.add_format({
            'font_size': 9, 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'border_color': '#E2E8F0', 'num_format': 'yyyy-mm-dd',
        })
        f['date_z'] = workbook.add_format({
            'font_size': 9, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#F8FAFC', 'border': 1, 'border_color': '#E2E8F0', 'num_format': 'yyyy-mm-dd',
        })

        # Status Badges
        f['status_green'] = workbook.add_format({
            'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
            'font_color': '#047857', 'bg_color': '#ECFDF5',
            'border': 1, 'border_color': '#A7F3D0',
        })
        f['status_red'] = workbook.add_format({
            'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
            'font_color': '#B91C1C', 'bg_color': '#FEF2F2',
            'border': 1, 'border_color': '#FECACA',
        })
        f['status_yellow'] = workbook.add_format({
            'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
            'font_color': '#B45309', 'bg_color': '#FFFBEB',
            'border': 1, 'border_color': '#FDE68A',
        })
        f['status_blue'] = workbook.add_format({
            'bold': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter',
            'font_color': '#1D4ED8', 'bg_color': '#EFF6FF',
            'border': 1, 'border_color': '#BFDBFE',
        })

        # Total Rows
        f['total_lbl'] = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'left', 'valign': 'vcenter',
            'top': 1, 'top_color': '#0F172A',
            'bottom': 6, 'bottom_color': '#0F172A',
            'bg_color': '#F1F5F9',
        })
        f['total_curr'] = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'right', 'valign': 'vcenter',
            'top': 1, 'top_color': '#0F172A',
            'bottom': 6, 'bottom_color': '#0F172A',
            'bg_color': '#F1F5F9',
            'num_format': '$#,##0.00',
        })
        f['total_num'] = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'right', 'valign': 'vcenter',
            'top': 1, 'top_color': '#0F172A',
            'bottom': 6, 'bottom_color': '#0F172A',
            'bg_color': '#F1F5F9',
            'num_format': '#,##0',
        })
        f['total_pct'] = workbook.add_format({
            'bold': True, 'font_size': 10, 'align': 'right', 'valign': 'vcenter',
            'top': 1, 'top_color': '#0F172A',
            'bottom': 6, 'bottom_color': '#0F172A',
            'bg_color': '#F1F5F9',
            'num_format': '0.0%',
        })

        f['empty_info'] = workbook.add_format({
            'italic': True, 'font_size': 10, 'align': 'center', 'valign': 'vcenter',
            'font_color': '#64748B', 'bg_color': '#F8FAFC',
            'border': 1, 'border_color': '#E2E8F0',
        })

        return f

    @classmethod
    def _write_banner(cls, ws, f, title, subtitle, company_name, user_name, filter_info, last_col_idx):
        """Writes top school brand banner."""
        ws.set_row(0, 30)
        ws.set_row(1, 22)
        ws.set_row(2, 18)

        # Row 0: School Name / Primary Title
        ws.merge_range(0, 0, 0, max(last_col_idx - 2, 1), f"  {company_name or 'School Management System'}", f['title'])
        ws.merge_range(0, max(last_col_idx - 1, 2), 0, last_col_idx, "OFFICIAL REPORT", f['title_right'])

        # Row 1: Subtitle (Report Name)
        ws.merge_range(1, 0, 1, max(last_col_idx - 2, 1), f"  {title.upper()}", f['subtitle'])
        gen_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        ws.merge_range(1, max(last_col_idx - 1, 2), 1, last_col_idx, f"Generated: {gen_time}", f['subtitle_right'])

        # Row 2: Metadata / Filter info
        user_str = f"Exported by: {user_name or 'Administrator'}"
        filter_str = f" | Filters: {filter_info}" if filter_info else " | Filters: All Records"
        ws.merge_range(2, 0, 2, last_col_idx, f"  {user_str}{filter_str}", f['meta_bar'])

    @classmethod
    def _autofit(cls, ws, col_widths, padding=3):
        """Sets column widths safely based on computed content lengths."""
        for col_idx, width in col_widths.items():
            final_width = max(width + padding, 10)
            ws.set_column(col_idx, col_idx, min(final_width, 45))

    # =========================================================================
    # 1. FEE & INVOICES REPORT
    # =========================================================================
    @classmethod
    def generate_fee_report(cls, env, domain=None, ids=None, filter_desc=''):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        f = cls._create_formats(wb)

        if ids:
            fees = env['school.fee'].browse(ids)
        elif domain is not None:
            fees = env['school.fee'].search(domain)
        else:
            fees = env['school.fee'].search([])

        ws = wb.add_worksheet('Fee Invoices')
        ws.set_tab_color('#1E3A8A')
        ws.freeze_panes(8, 0)

        # Company & user
        comp = env.company.name or 'School Management'
        user = env.user.name or 'Admin'

        # Banner
        headers = [
            '#', 'Receipt #', 'Student Name', 'Student ID', 'Class',
            'Fee Type', 'Invoiced ($)', 'Paid ($)', 'Balance ($)',
            'Due Date', 'Paid Date', 'Status', 'Payment Method', 'Notes'
        ]
        last_col = len(headers) - 1
        cls._write_banner(ws, f, "Student Fee & Invoices Statement", "", comp, user, filter_desc, last_col)

        # KPI Summary Cards (Rows 4-5)
        total_inv = sum(fees.mapped('amount'))
        total_paid = sum(fees.mapped('paid_amount'))
        total_bal = sum(fees.mapped('balance'))
        col_rate = (total_paid / total_inv) if total_inv else 0.0
        overdue_cnt = len(fees.filtered(lambda r: r.status == 'overdue'))

        ws.set_row(4, 18)
        ws.set_row(5, 24)

        kpis = [
            (0, 1, 'TOTAL INVOICED', total_inv, f['kpi_curr']),
            (2, 3, 'TOTAL COLLECTED', total_paid, f['kpi_curr']),
            (4, 5, 'OUTSTANDING BALANCE', total_bal, f['kpi_curr_red'] if total_bal > 0 else f['kpi_curr']),
            (6, 7, 'COLLECTION RATE', col_rate, f['kpi_pct']),
            (8, 9, 'TOTAL INVOICES', len(fees), f['kpi_num']),
            (10, 11, 'OVERDUE INVOICES', overdue_cnt, f['kpi_num']),
        ]
        for c1, c2, title, val, v_fmt in kpis:
            if c2 <= last_col:
                ws.merge_range(4, c1, 4, c2, title, f['kpi_title'])
                ws.merge_range(5, c1, 5, c2, val, v_fmt)

        # Table Header (Row 7)
        ws.set_row(7, 24)
        col_lens = {i: len(h) for i, h in enumerate(headers)}
        for i, h in enumerate(headers):
            align_fmt = f['th_right'] if i in (6, 7, 8) else (f['th_center'] if i in (0, 1, 9, 10, 11) else f['th_left'])
            ws.write(7, i, h, align_fmt)

        fee_type_dict = dict(env['school.fee']._fields['fee_type'].selection)
        status_dict = dict(env['school.fee']._fields['status'].selection)
        pay_method_dict = dict(env['school.fee']._fields['payment_method'].selection)

        start_row = 8
        cur_row = start_row

        if not fees:
            ws.merge_range(cur_row, 0, cur_row + 1, last_col, "No fee records found matching criteria.", f['empty_info'])
            cur_row += 2
        else:
            for idx, rec in enumerate(fees, start=1):
                z = idx % 2 == 0
                ws.set_row(cur_row, 20)

                st_badge = f['status_green'] if rec.status == 'paid' else (
                    f['status_red'] if rec.status == 'overdue' else (
                        f['status_yellow'] if rec.status == 'pending' else f['status_blue']
                    )
                )

                vals = [
                    (idx, f['td_center_z'] if z else f['td_center']),
                    (rec.receipt_number or '-', f['td_center_z'] if z else f['td_center']),
                    (rec.student_id.name or '', f['td_left_z'] if z else f['td_left']),
                    (rec.student_id.student_id or '', f['td_center_z'] if z else f['td_center']),
                    (rec.class_id.name or '', f['td_left_z'] if z else f['td_left']),
                    (fee_type_dict.get(rec.fee_type, rec.fee_type or ''), f['td_left_z'] if z else f['td_left']),
                    (rec.amount or 0.0, f['curr_z'] if z else f['curr']),
                    (rec.paid_amount or 0.0, f['curr_z'] if z else f['curr']),
                    (rec.balance or 0.0, f['curr_z'] if z else f['curr']),
                    (rec.due_date.strftime('%Y-%m-%d') if rec.due_date else '', f['date_z'] if z else f['date']),
                    (rec.paid_date.strftime('%Y-%m-%d') if rec.paid_date else '', f['date_z'] if z else f['date']),
                    (status_dict.get(rec.status, rec.status or '').upper(), st_badge),
                    (pay_method_dict.get(rec.payment_method, rec.payment_method or '').capitalize(), f['td_left_z'] if z else f['td_left']),
                    (rec.notes or '', f['td_left_z'] if z else f['td_left']),
                ]

                for col_i, (val, fmt_cell) in enumerate(vals):
                    ws.write(cur_row, col_i, val, fmt_cell)
                    col_lens[col_i] = max(col_lens[col_i], len(str(val or '')))

                cur_row += 1

            # Total Formula Row
            ws.set_row(cur_row, 22)
            ws.merge_range(cur_row, 0, cur_row, 5, "TOTAL SUMMARY", f['total_lbl'])
            ws.write_formula(cur_row, 6, f"=SUM(G{start_row+1}:G{cur_row})", f['total_curr'], total_inv)
            ws.write_formula(cur_row, 7, f"=SUM(H{start_row+1}:H{cur_row})", f['total_curr'], total_paid)
            ws.write_formula(cur_row, 8, f"=SUM(I{start_row+1}:I{cur_row})", f['total_curr'], total_bal)
            for empty_col in range(9, last_col + 1):
                ws.write(cur_row, empty_col, '', f['total_lbl'])

        cls._autofit(ws, col_lens)

        # ---------------------------------------------------------------------
        # Sheet 2: Financial Analytics Breakdown
        # ---------------------------------------------------------------------
        ws2 = wb.add_worksheet('Financial Analytics')
        ws2.set_tab_color('#3B82F6')
        cls._write_banner(ws2, f, "Fee Category & Status Analytics", "", comp, user, filter_desc, 5)

        ws2.write(4, 0, "BREAKDOWN BY FEE TYPE", f['sec_header'])
        h2 = ['Fee Type', 'Invoices Count', 'Invoiced ($)', 'Paid ($)', 'Balance ($)', '% Collected']
        ws2.set_row(5, 20)
        for i, h in enumerate(h2):
            ws2.write(5, i, h, f['th_right'] if i >= 1 else f['th_left'])

        r2 = 6
        for ftype_key, ftype_name in fee_type_dict.items():
            subset = fees.filtered(lambda r: r.fee_type == ftype_key)
            if subset:
                sub_inv = sum(subset.mapped('amount'))
                sub_paid = sum(subset.mapped('paid_amount'))
                sub_bal = sum(subset.mapped('balance'))
                sub_pct = (sub_paid / sub_inv) if sub_inv else 0.0
                ws2.write(r2, 0, ftype_name, f['td_left'])
                ws2.write(r2, 1, len(subset), f['num'])
                ws2.write(r2, 2, sub_inv, f['curr'])
                ws2.write(r2, 3, sub_paid, f['curr'])
                ws2.write(r2, 4, sub_bal, f['curr'])
                ws2.write(r2, 5, sub_pct, f['pct'])
                r2 += 1

        r2 += 2
        ws2.write(r2, 0, "BREAKDOWN BY PAYMENT STATUS", f['sec_header'])
        r2 += 1
        h3 = ['Status', 'Count', 'Total Amount ($)', 'Paid Amount ($)', 'Balance ($)', '% of Total']
        ws2.set_row(r2, 20)
        for i, h in enumerate(h3):
            ws2.write(r2, i, h, f['th_right'] if i >= 1 else f['th_left'])
        r2 += 1

        for st_key, st_name in status_dict.items():
            subset = fees.filtered(lambda r: r.status == st_key)
            if subset:
                sub_inv = sum(subset.mapped('amount'))
                sub_paid = sum(subset.mapped('paid_amount'))
                sub_bal = sum(subset.mapped('balance'))
                pct_tot = (sub_inv / total_inv) if total_inv else 0.0
                ws2.write(r2, 0, st_name, f['td_left'])
                ws2.write(r2, 1, len(subset), f['num'])
                ws2.write(r2, 2, sub_inv, f['curr'])
                ws2.write(r2, 3, sub_paid, f['curr'])
                ws2.write(r2, 4, sub_bal, f['curr'])
                ws2.write(r2, 5, pct_tot, f['pct'])
                r2 += 1

        cls._autofit(ws2, {0: 22, 1: 15, 2: 18, 3: 18, 4: 18, 5: 15})

        wb.close()
        return output.getvalue()

    # =========================================================================
    # 2. ANNUAL TUITION & YEAR PAYMENTS REPORT
    # =========================================================================
    @classmethod
    def generate_year_payment_report(cls, env, domain=None, ids=None, filter_desc=''):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        f = cls._create_formats(wb)

        if ids:
            payments = env['school.student.year.payment'].browse(ids)
        elif domain is not None:
            payments = env['school.student.year.payment'].search(domain)
        else:
            payments = env['school.student.year.payment'].search([])

        ws = wb.add_worksheet('Tuition Payments')
        ws.set_tab_color('#047857')
        ws.freeze_panes(8, 0)

        comp = env.company.name or 'School Management'
        user = env.user.name or 'Admin'

        headers = [
            '#', 'Receipt #', 'Student Name', 'Student ID', 'Class', 'Academic Year',
            'Annual Tuition ($)', 'Total Paid ($)', 'Balance ($)', 'Overall Status',
            'Inst 1 Amount ($)', 'Inst 1 Due', 'Inst 1 Paid', 'Inst 1 Status',
            'Inst 2 Amount ($)', 'Inst 2 Due', 'Inst 2 Paid', 'Inst 2 Status',
            'Next Deadline', 'Payment Method', 'Notes'
        ]
        last_col = len(headers) - 1
        cls._write_banner(ws, f, "Annual Student Tuition & Payments Statement", "", comp, user, filter_desc, last_col)

        tot_tuition = sum(payments.mapped('total_amount'))
        tot_paid = sum(payments.mapped('total_paid'))
        tot_bal = sum(payments.mapped('total_balance'))
        rate = (tot_paid / tot_tuition) if tot_tuition else 0.0

        ws.set_row(4, 18)
        ws.set_row(5, 24)
        kpis = [
            (0, 2, 'TOTAL ANNUAL TUITION', tot_tuition, f['kpi_curr']),
            (3, 5, 'TOTAL COLLECTED', tot_paid, f['kpi_curr']),
            (6, 8, 'REMAINING BALANCE', tot_bal, f['kpi_curr_red'] if tot_bal > 0 else f['kpi_curr']),
            (9, 11, 'COLLECTION RATE', rate, f['kpi_pct']),
            (12, 14, 'TOTAL STUDENTS ENROLLED', len(payments), f['kpi_num']),
        ]
        for c1, c2, title, val, v_fmt in kpis:
            if c2 <= last_col:
                ws.merge_range(4, c1, 4, c2, title, f['kpi_title'])
                ws.merge_range(5, c1, 5, c2, val, v_fmt)

        ws.set_row(7, 24)
        col_lens = {i: len(h) for i, h in enumerate(headers)}
        for i, h in enumerate(headers):
            is_num = i in (6, 7, 8, 10, 14)
            align_fmt = f['th_right'] if is_num else (f['th_center'] if i in (0, 1, 3, 5, 9, 11, 12, 13, 15, 16, 17, 18) else f['th_left'])
            ws.write(7, i, h, align_fmt)

        st_dict = dict(env['school.student.year.payment']._fields['overall_status'].selection)
        inst_st_dict = dict(env['school.student.year.payment']._fields['installment_1_status'].selection)

        start_row = 8
        cur_row = start_row

        if not payments:
            ws.merge_range(cur_row, 0, cur_row + 1, last_col, "No payment records found matching criteria.", f['empty_info'])
            cur_row += 2
        else:
            for idx, rec in enumerate(payments, start=1):
                z = idx % 2 == 0
                ws.set_row(cur_row, 20)

                st_badge = f['status_green'] if rec.overall_status == 'paid' else (
                    f['status_yellow'] if rec.overall_status == 'partial' else f['status_red']
                )

                vals = [
                    (idx, f['td_center_z'] if z else f['td_center']),
                    (rec.receipt_number or '-', f['td_center_z'] if z else f['td_center']),
                    (rec.student_id.name or '', f['td_left_z'] if z else f['td_left']),
                    (rec.student_id.student_id or '', f['td_center_z'] if z else f['td_center']),
                    (rec.class_id.name or '', f['td_left_z'] if z else f['td_left']),
                    (rec.year or '', f['td_center_z'] if z else f['td_center']),
                    (rec.total_amount or 0.0, f['curr_z'] if z else f['curr']),
                    (rec.total_paid or 0.0, f['curr_z'] if z else f['curr']),
                    (rec.total_balance or 0.0, f['curr_z'] if z else f['curr']),
                    (st_dict.get(rec.overall_status, rec.overall_status or '').upper(), st_badge),
                    (rec.installment_1_amount or 0.0, f['curr_z'] if z else f['curr']),
                    (rec.installment_1_due_date.strftime('%Y-%m-%d') if rec.installment_1_due_date else '', f['date_z'] if z else f['date']),
                    (rec.installment_1_paid_date.strftime('%Y-%m-%d') if rec.installment_1_paid_date else '', f['date_z'] if z else f['date']),
                    (inst_st_dict.get(rec.installment_1_status, rec.installment_1_status or '').capitalize(), f['td_center_z'] if z else f['td_center']),
                    (rec.installment_2_amount or 0.0, f['curr_z'] if z else f['curr']),
                    (rec.installment_2_due_date.strftime('%Y-%m-%d') if rec.installment_2_due_date else '', f['date_z'] if z else f['date']),
                    (rec.installment_2_paid_date.strftime('%Y-%m-%d') if rec.installment_2_paid_date else '', f['date_z'] if z else f['date']),
                    (inst_st_dict.get(rec.installment_2_status, rec.installment_2_status or '').capitalize(), f['td_center_z'] if z else f['td_center']),
                    (rec.next_deadline.strftime('%Y-%m-%d') if rec.next_deadline else '', f['date_z'] if z else f['date']),
                    ((rec.payment_method or '').capitalize(), f['td_left_z'] if z else f['td_left']),
                    (rec.notes or '', f['td_left_z'] if z else f['td_left']),
                ]

                for col_i, (val, fmt_cell) in enumerate(vals):
                    ws.write(cur_row, col_i, val, fmt_cell)
                    col_lens[col_i] = max(col_lens[col_i], len(str(val or '')))

                cur_row += 1

            ws.set_row(cur_row, 22)
            ws.merge_range(cur_row, 0, cur_row, 5, "TOTAL SUMMARY", f['total_lbl'])
            ws.write_formula(cur_row, 6, f"=SUM(G{start_row+1}:G{cur_row})", f['total_curr'], tot_tuition)
            ws.write_formula(cur_row, 7, f"=SUM(H{start_row+1}:H{cur_row})", f['total_curr'], tot_paid)
            ws.write_formula(cur_row, 8, f"=SUM(I{start_row+1}:I{cur_row})", f['total_curr'], tot_bal)
            for c in range(9, last_col + 1):
                ws.write(cur_row, c, '', f['total_lbl'])

        cls._autofit(ws, col_lens)
        wb.close()
        return output.getvalue()

    # =========================================================================
    # 3. ATTENDANCE LOG & SUMMARY REPORT
    # =========================================================================
    @classmethod
    def generate_attendance_report(cls, env, domain=None, ids=None, filter_desc=''):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        f = cls._create_formats(wb)

        if ids:
            attendances = env['school.attendance'].browse(ids)
        elif domain is not None:
            attendances = env['school.attendance'].search(domain)
        else:
            attendances = env['school.attendance'].search([])

        ws = wb.add_worksheet('Attendance Log')
        ws.set_tab_color('#2563EB')
        ws.freeze_panes(8, 0)

        comp = env.company.name or 'School Management'
        user = env.user.name or 'Admin'

        headers = ['#', 'Date', 'Student Name', 'Student ID', 'Class', 'Status', 'Remarks / Notes']
        last_col = len(headers) - 1
        cls._write_banner(ws, f, "Student Attendance Tracking Log", "", comp, user, filter_desc, last_col)

        tot_recs = len(attendances)
        present_cnt = len(attendances.filtered(lambda a: a.status == 'present'))
        absent_cnt = len(attendances.filtered(lambda a: a.status == 'absent'))
        late_cnt = len(attendances.filtered(lambda a: a.status == 'late'))
        excused_cnt = len(attendances.filtered(lambda a: a.status == 'excused'))
        rate = (present_cnt / tot_recs) if tot_recs else 0.0

        ws.set_row(4, 18)
        ws.set_row(5, 24)
        kpis = [
            (0, 0, 'TOTAL LOGS', tot_recs, f['kpi_num']),
            (1, 1, 'PRESENT', present_cnt, f['kpi_num']),
            (2, 2, 'ABSENT', absent_cnt, f['kpi_num']),
            (3, 3, 'LATE', late_cnt, f['kpi_num']),
            (4, 4, 'EXCUSED', excused_cnt, f['kpi_num']),
            (5, 6, 'ATTENDANCE RATE', rate, f['kpi_pct']),
        ]
        for c1, c2, title, val, v_fmt in kpis:
            if c2 <= last_col:
                if c1 == c2:
                    ws.write(4, c1, title, f['kpi_title'])
                    ws.write(5, c1, val, v_fmt)
                else:
                    ws.merge_range(4, c1, 4, c2, title, f['kpi_title'])
                    ws.merge_range(5, c1, 5, c2, val, v_fmt)

        ws.set_row(7, 24)
        col_lens = {i: len(h) for i, h in enumerate(headers)}
        for i, h in enumerate(headers):
            align_fmt = f['th_center'] if i in (0, 1, 3, 5) else f['th_left']
            ws.write(7, i, h, align_fmt)

        status_dict = dict(env['school.attendance']._fields['status'].selection)

        cur_row = 8
        if not attendances:
            ws.merge_range(cur_row, 0, cur_row + 1, last_col, "No attendance records found matching criteria.", f['empty_info'])
            cur_row += 2
        else:
            for idx, rec in enumerate(attendances, start=1):
                z = idx % 2 == 0
                ws.set_row(cur_row, 20)

                st_badge = f['status_green'] if rec.status == 'present' else (
                    f['status_red'] if rec.status == 'absent' else (
                        f['status_yellow'] if rec.status == 'late' else f['status_blue']
                    )
                )

                vals = [
                    (idx, f['td_center_z'] if z else f['td_center']),
                    (rec.date.strftime('%Y-%m-%d') if rec.date else '', f['date_z'] if z else f['date']),
                    (rec.student_id.name or '', f['td_left_z'] if z else f['td_left']),
                    (rec.student_id.student_id or '', f['td_center_z'] if z else f['td_center']),
                    (rec.class_id.name or '', f['td_left_z'] if z else f['td_left']),
                    (status_dict.get(rec.status, rec.status or '').upper(), st_badge),
                    (rec.notes or '', f['td_left_z'] if z else f['td_left']),
                ]

                for col_i, (val, fmt_cell) in enumerate(vals):
                    ws.write(cur_row, col_i, val, fmt_cell)
                    col_lens[col_i] = max(col_lens[col_i], len(str(val or '')))

                cur_row += 1

        cls._autofit(ws, col_lens)

        # ---------------------------------------------------------------------
        # Sheet 2: Student Summary Breakdown
        # ---------------------------------------------------------------------
        ws2 = wb.add_worksheet('Student Summary')
        ws2.set_tab_color('#10B981')
        cls._write_banner(ws2, f, "Attendance Summary per Student", "", comp, user, filter_desc, 7)

        h2 = ['#', 'Student ID', 'Student Name', 'Class', 'Total Days', 'Present Days', 'Absent Days', 'Attendance Rate %']
        ws2.set_row(4, 22)
        for i, h in enumerate(h2):
            ws2.write(4, i, h, f['th_right'] if i >= 4 else (f['th_center'] if i in (0, 1) else f['th_left']))

        students = attendances.mapped('student_id')
        r2 = 5
        col_lens2 = {i: len(h) for i, h in enumerate(h2)}
        for s_idx, stu in enumerate(students, start=1):
            s_recs = attendances.filtered(lambda a: a.student_id == stu)
            tot_s = len(s_recs)
            pres_s = len(s_recs.filtered(lambda a: a.status == 'present'))
            abs_s = len(s_recs.filtered(lambda a: a.status == 'absent'))
            rate_s = (pres_s / tot_s) if tot_s else 0.0

            z = s_idx % 2 == 0
            ws2.set_row(r2, 20)
            pct_style = f['pct_z'] if z else f['pct']
            if rate_s < 0.80:
                pct_style = f['status_red']

            vals2 = [
                (s_idx, f['td_center_z'] if z else f['td_center']),
                (stu.student_id or '', f['td_center_z'] if z else f['td_center']),
                (stu.name or '', f['td_left_z'] if z else f['td_left']),
                (stu.class_id.name or '', f['td_left_z'] if z else f['td_left']),
                (tot_s, f['num_z'] if z else f['num']),
                (pres_s, f['num_z'] if z else f['num']),
                (abs_s, f['num_z'] if z else f['num']),
                (rate_s, pct_style),
            ]
            for col_i, (val, fmt_cell) in enumerate(vals2):
                ws2.write(r2, col_i, val, fmt_cell)
                col_lens2[col_i] = max(col_lens2[col_i], len(str(val or '')))
            r2 += 1

        cls._autofit(ws2, col_lens2)

        wb.close()
        return output.getvalue()

    # =========================================================================
    # 4. EXAM GRADES & RESULTS REPORT
    # =========================================================================
    @classmethod
    def generate_grade_report(cls, env, domain=None, ids=None, filter_desc=''):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        f = cls._create_formats(wb)

        if ids:
            grades = env['school.grade'].browse(ids)
        elif domain is not None:
            grades = env['school.grade'].search(domain)
        else:
            grades = env['school.grade'].search([])

        ws = wb.add_worksheet('Exam Grades')
        ws.set_tab_color('#7C3AED')
        ws.freeze_panes(8, 0)

        comp = env.company.name or 'School Management'
        user = env.user.name or 'Admin'

        headers = [
            '#', 'Student Name', 'Student ID', 'Class', 'Exam', 'Subject',
            'Exam Date/Time', 'Room/Seat', 'Attendance', 'Marks Obtained',
            'Max Marks', 'Percentage (%)', 'Grade', 'Result', 'Remarks'
        ]
        last_col = len(headers) - 1
        cls._write_banner(ws, f, "Student Examination Grades & Results Statement", "", comp, user, filter_desc, last_col)

        tot_grades = len(grades)
        avg_pct = (sum(grades.mapped('percentage')) / tot_grades) / 100.0 if tot_grades else 0.0
        pass_cnt = len(grades.filtered(lambda g: g.result == 'pass'))
        fail_cnt = len(grades.filtered(lambda g: g.result == 'fail'))
        pass_rate = (pass_cnt / tot_grades) if tot_grades else 0.0

        ws.set_row(4, 18)
        ws.set_row(5, 24)
        kpis = [
            (0, 2, 'TOTAL EXAM ENTRIES', tot_grades, f['kpi_num']),
            (3, 5, 'AVERAGE SCORE', avg_pct, f['kpi_pct']),
            (6, 8, 'PASSED EXAMS', pass_cnt, f['kpi_num']),
            (9, 11, 'FAILED EXAMS', fail_cnt, f['kpi_num']),
            (12, 14, 'PASS RATE', pass_rate, f['kpi_pct']),
        ]
        for c1, c2, title, val, v_fmt in kpis:
            if c2 <= last_col:
                ws.merge_range(4, c1, 4, c2, title, f['kpi_title'])
                ws.merge_range(5, c1, 5, c2, val, v_fmt)

        ws.set_row(7, 24)
        col_lens = {i: len(h) for i, h in enumerate(headers)}
        for i, h in enumerate(headers):
            is_num = i in (9, 10, 11)
            align_fmt = f['th_right'] if is_num else (f['th_center'] if i in (0, 2, 6, 7, 8, 12, 13) else f['th_left'])
            ws.write(7, i, h, align_fmt)

        grade_letter_dict = dict(env['school.grade']._fields['grade_letter'].selection)
        result_dict = dict(env['school.grade']._fields['result'].selection)
        att_status_dict = dict(env['school.grade']._fields['attendance_status'].selection)

        cur_row = 8
        if not grades:
            ws.merge_range(cur_row, 0, cur_row + 1, last_col, "No grade records found matching criteria.", f['empty_info'])
            cur_row += 2
        else:
            for idx, rec in enumerate(grades, start=1):
                z = idx % 2 == 0
                ws.set_row(cur_row, 20)

                res_badge = f['status_green'] if rec.result == 'pass' else f['status_red']
                pct_dec = (rec.percentage / 100.0) if rec.percentage else 0.0

                exam_dt_str = rec.exam_datetime.strftime('%Y-%m-%d %H:%M') if rec.exam_datetime else ''

                vals = [
                    (idx, f['td_center_z'] if z else f['td_center']),
                    (rec.student_id.name or '', f['td_left_z'] if z else f['td_left']),
                    (rec.student_id.student_id or '', f['td_center_z'] if z else f['td_center']),
                    (rec.class_id.name or '', f['td_left_z'] if z else f['td_left']),
                    (rec.exam_id.name or '', f['td_left_z'] if z else f['td_left']),
                    (rec.subject_id.name or '', f['td_left_z'] if z else f['td_left']),
                    (exam_dt_str, f['td_center_z'] if z else f['td_center']),
                    (rec.room or '', f['td_center_z'] if z else f['td_center']),
                    (att_status_dict.get(rec.attendance_status, rec.attendance_status or '').capitalize(), f['td_center_z'] if z else f['td_center']),
                    (rec.marks_obtained or 0.0, f['num_z'] if z else f['num']),
                    (rec.total_marks or 0, f['num_z'] if z else f['num']),
                    (pct_dec, f['pct_z'] if z else f['pct']),
                    (grade_letter_dict.get(rec.grade_letter, rec.grade_letter or '').upper(), f['td_center_z'] if z else f['td_center']),
                    (result_dict.get(rec.result, rec.result or '').upper(), res_badge),
                    (rec.remarks or '', f['td_left_z'] if z else f['td_left']),
                ]

                for col_i, (val, fmt_cell) in enumerate(vals):
                    ws.write(cur_row, col_i, val, fmt_cell)
                    col_lens[col_i] = max(col_lens[col_i], len(str(val or '')))

                cur_row += 1

        cls._autofit(ws, col_lens)

        # ---------------------------------------------------------------------
        # Sheet 2: Grade Analytics
        # ---------------------------------------------------------------------
        ws2 = wb.add_worksheet('Subject Analytics')
        ws2.set_tab_color('#8B5CF6')
        cls._write_banner(ws2, f, "Subject Performance & Grade Distribution", "", comp, user, filter_desc, 6)

        ws2.write(4, 0, "PERFORMANCE BY SUBJECT", f['sec_header'])
        h2 = ['Subject', 'Exam Count', 'Avg Score (%)', 'Pass Count', 'Fail Count', 'Pass Rate (%)']
        ws2.set_row(5, 20)
        for i, h in enumerate(h2):
            ws2.write(5, i, h, f['th_right'] if i >= 1 else f['th_left'])

        r2 = 6
        subjects = grades.mapped('subject_id')
        for sub in subjects:
            sub_grades = grades.filtered(lambda g: g.subject_id == sub)
            sub_tot = len(sub_grades)
            sub_avg = (sum(sub_grades.mapped('percentage')) / sub_tot) / 100.0 if sub_tot else 0.0
            sub_p = len(sub_grades.filtered(lambda g: g.result == 'pass'))
            sub_f = len(sub_grades.filtered(lambda g: g.result == 'fail'))
            sub_prate = (sub_p / sub_tot) if sub_tot else 0.0

            ws2.write(r2, 0, sub.name or 'Unknown', f['td_left'])
            ws2.write(r2, 1, sub_tot, f['num'])
            ws2.write(r2, 2, sub_avg, f['pct'])
            ws2.write(r2, 3, sub_p, f['num'])
            ws2.write(r2, 4, sub_f, f['num'])
            ws2.write(r2, 5, sub_prate, f['pct'])
            r2 += 1

        cls._autofit(ws2, {0: 25, 1: 15, 2: 15, 3: 15, 4: 15, 5: 15})

        wb.close()
        return output.getvalue()

    # =========================================================================
    # 5. STUDENT MASTER ROSTER & DIRECTORY
    # =========================================================================
    @classmethod
    def generate_student_report(cls, env, domain=None, ids=None, filter_desc=''):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        f = cls._create_formats(wb)

        if ids:
            students = env['school.student'].browse(ids)
        elif domain is not None:
            students = env['school.student'].search(domain)
        else:
            students = env['school.student'].search([])

        ws = wb.add_worksheet('Students Roster')
        ws.set_tab_color('#0D9488')
        ws.freeze_panes(8, 0)

        comp = env.company.name or 'School Management'
        user = env.user.name or 'Admin'

        headers = [
            '#', 'Student ID', 'Full Name', 'Gender', 'Date of Birth', 'Age',
            'Class', 'Academic Period', 'Status', 'Enrollment Date',
            'Average Score (%)', 'Overall Grade', 'GPA (4.0)', 'Attendance Rate (%)',
            'Tuition Total ($)', 'Tuition Paid ($)', 'Tuition Balance ($)',
            'Email', 'Phone', 'Parent / Guardian', 'Parent Phone'
        ]
        last_col = len(headers) - 1
        cls._write_banner(ws, f, "Student Master Directory & Academic Profiles", "", comp, user, filter_desc, last_col)

        tot_students = len(students)
        active_cnt = len(students.filtered(lambda s: s.study_status == 'enrolled'))
        avg_score = (sum(students.mapped('average_score')) / tot_students) / 100.0 if tot_students else 0.0
        avg_att = (sum(students.mapped('attendance_rate')) / tot_students) / 100.0 if tot_students else 0.0
        tot_bal = sum(students.mapped('total_year_balance'))

        ws.set_row(4, 18)
        ws.set_row(5, 24)
        kpis = [
            (0, 3, 'TOTAL STUDENTS', tot_students, f['kpi_num']),
            (4, 7, 'CURRENTLY ENROLLED', active_cnt, f['kpi_num']),
            (8, 11, 'AVG ACADEMIC SCORE', avg_score, f['kpi_pct']),
            (12, 15, 'AVG ATTENDANCE RATE', avg_att, f['kpi_pct']),
            (16, 19, 'TOTAL OUTSTANDING FEES', tot_bal, f['kpi_curr_red'] if tot_bal > 0 else f['kpi_curr']),
        ]
        for c1, c2, title, val, v_fmt in kpis:
            if c2 <= last_col:
                ws.merge_range(4, c1, 4, c2, title, f['kpi_title'])
                ws.merge_range(5, c1, 5, c2, val, v_fmt)

        ws.set_row(7, 24)
        col_lens = {i: len(h) for i, h in enumerate(headers)}
        for i, h in enumerate(headers):
            is_num = i in (5, 10, 12, 13, 14, 15)
            align_fmt = f['th_right'] if is_num else (f['th_center'] if i in (0, 1, 3, 4, 7, 8, 9, 11) else f['th_left'])
            ws.write(7, i, h, align_fmt)

        gender_dict = dict(env['school.student']._fields['gender'].selection)
        status_dict = dict(env['school.student']._fields['study_status'].selection)

        cur_row = 8
        if not students:
            ws.merge_range(cur_row, 0, cur_row + 1, last_col, "No student records found.", f['empty_info'])
            cur_row += 2
        else:
            for idx, rec in enumerate(students, start=1):
                z = idx % 2 == 0
                ws.set_row(cur_row, 20)

                st_badge = f['status_green'] if rec.study_status == 'enrolled' else (
                    f['status_red'] if rec.study_status == 'stopped' else f['status_blue']
                )

                score_dec = (rec.average_score / 100.0) if rec.average_score else 0.0
                att_dec = (rec.attendance_rate / 100.0) if rec.attendance_rate else 0.0

                vals = [
                    (idx, f['td_center_z'] if z else f['td_center']),
                    (rec.student_id or '', f['td_center_z'] if z else f['td_center']),
                    (rec.name or '', f['td_left_z'] if z else f['td_left']),
                    (gender_dict.get(rec.gender, rec.gender or '').capitalize(), f['td_center_z'] if z else f['td_center']),
                    (rec.date_of_birth.strftime('%Y-%m-%d') if rec.date_of_birth else '', f['date_z'] if z else f['date']),
                    (rec.age or 0, f['num_z'] if z else f['num']),
                    (rec.class_id.name or '', f['td_left_z'] if z else f['td_left']),
                    (rec.study_period or '', f['td_center_z'] if z else f['td_center']),
                    (status_dict.get(rec.study_status, rec.study_status or '').upper(), st_badge),
                    (rec.enrollment_date.strftime('%Y-%m-%d') if rec.enrollment_date else '', f['date_z'] if z else f['date']),
                    (score_dec, f['pct_z'] if z else f['pct']),
                    (rec.academic_performance or '', f['td_center_z'] if z else f['td_center']),
                    (rec.gpa or 0.0, f['num_z'] if z else f['num']),
                    (att_dec, f['pct_z'] if z else f['pct']),
                    (rec.total_year_amount or 0.0, f['curr_z'] if z else f['curr']),
                    (rec.total_year_paid or 0.0, f['curr_z'] if z else f['curr']),
                    (rec.total_year_balance or 0.0, f['curr_z'] if z else f['curr']),
                    (rec.email or '', f['td_left_z'] if z else f['td_left']),
                    (rec.phone or '', f['td_left_z'] if z else f['td_left']),
                    (rec.parent_name or '', f['td_left_z'] if z else f['td_left']),
                    (rec.parent_phone or '', f['td_left_z'] if z else f['td_left']),
                ]

                for col_i, (val, fmt_cell) in enumerate(vals):
                    ws.write(cur_row, col_i, val, fmt_cell)
                    col_lens[col_i] = max(col_lens[col_i], len(str(val or '')))

                cur_row += 1

        cls._autofit(ws, col_lens)
        wb.close()
        return output.getvalue()

    # =========================================================================
    # 6. CLASS & ENROLLMENT OVERVIEW
    # =========================================================================
    @classmethod
    def generate_class_report(cls, env, domain=None, ids=None, filter_desc=''):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        f = cls._create_formats(wb)

        if ids:
            classes = env['school.class'].browse(ids)
        elif domain is not None:
            classes = env['school.class'].search(domain)
        else:
            classes = env['school.class'].search([])

        ws = wb.add_worksheet('Classes Overview')
        ws.set_tab_color('#0369A1')
        ws.freeze_panes(8, 0)

        comp = env.company.name or 'School Management'
        user = env.user.name or 'Admin'

        headers = [
            '#', 'Class Name', 'Code', 'Class Teacher', 'Room', 'Academic Year',
            'Enrolled Students', 'Capacity', 'Capacity %', 'Total Expected ($)',
            'Total Collected ($)', 'Collection Rate %'
        ]
        last_col = len(headers) - 1
        cls._write_banner(ws, f, "Class Directory & Capacity Overview", "", comp, user, filter_desc, last_col)

        tot_classes = len(classes)
        tot_students = sum(classes.mapped('student_count'))
        tot_cap = sum(classes.mapped('capacity'))
        cap_pct = (tot_students / tot_cap) if tot_cap else 0.0

        ws.set_row(4, 18)
        ws.set_row(5, 24)
        kpis = [
            (0, 2, 'TOTAL CLASSES', tot_classes, f['kpi_num']),
            (3, 5, 'TOTAL STUDENTS', tot_students, f['kpi_num']),
            (6, 8, 'TOTAL CAPACITY', tot_cap, f['kpi_num']),
            (9, 11, 'OVERALL OCCUPANCY', cap_pct, f['kpi_pct']),
        ]
        for c1, c2, title, val, v_fmt in kpis:
            if c2 <= last_col:
                ws.merge_range(4, c1, 4, c2, title, f['kpi_title'])
                ws.merge_range(5, c1, 5, c2, val, v_fmt)

        ws.set_row(7, 24)
        col_lens = {i: len(h) for i, h in enumerate(headers)}
        for i, h in enumerate(headers):
            is_num = i in (6, 7, 8, 9, 10, 11)
            align_fmt = f['th_right'] if is_num else (f['th_center'] if i in (0, 2, 4, 5) else f['th_left'])
            ws.write(7, i, h, align_fmt)

        cur_row = 8
        for idx, rec in enumerate(classes, start=1):
            z = idx % 2 == 0
            ws.set_row(cur_row, 20)

            cap_ratio = (rec.capacity_progress / 100.0) if rec.capacity_progress else 0.0
            col_ratio = (rec.payment_collection_rate / 100.0) if rec.payment_collection_rate else 0.0

            vals = [
                (idx, f['td_center_z'] if z else f['td_center']),
                (rec.name or '', f['td_left_z'] if z else f['td_left']),
                (rec.code or '', f['td_center_z'] if z else f['td_center']),
                (rec.teacher_id.name or '', f['td_left_z'] if z else f['td_left']),
                (rec.room or '', f['td_center_z'] if z else f['td_center']),
                (rec.payment_year or '', f['td_center_z'] if z else f['td_center']),
                (rec.student_count or 0, f['num_z'] if z else f['num']),
                (rec.capacity or 0, f['num_z'] if z else f['num']),
                (cap_ratio, f['pct_z'] if z else f['pct']),
                (rec.total_payment_expected or 0.0, f['curr_z'] if z else f['curr']),
                (rec.total_payment_collected or 0.0, f['curr_z'] if z else f['curr']),
                (col_ratio, f['pct_z'] if z else f['pct']),
            ]

            for col_i, (val, fmt_cell) in enumerate(vals):
                ws.write(cur_row, col_i, val, fmt_cell)
                col_lens[col_i] = max(col_lens[col_i], len(str(val or '')))

            cur_row += 1

        cls._autofit(ws, col_lens)
        wb.close()
        return output.getvalue()

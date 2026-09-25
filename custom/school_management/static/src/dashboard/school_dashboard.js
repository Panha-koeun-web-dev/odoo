/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { user } from "@web/core/user";
import { Component, onWillStart, useEffect, useRef, useState } from "@odoo/owl";

export class SchoolDashboard extends Component {
  static template = "school_management.SchoolDashboardMain";
  static props = ["*"];

  setup() {
    super.setup();
    this.orm = useService("orm");
    this.action = useService("action");
    this.user = user;

    this.state = useState({
      loading: true,
      data: null,
      lastUpdated: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    });

    this.genderChartRef = useRef("genderChartCanvas");
    this.attendanceChartRef = useRef("attendanceChartCanvas");
    this.attendanceTrendChartRef = useRef("attendanceTrendChartCanvas");
    this.feeStatusChartRef = useRef("feeStatusChartCanvas");
    this.feeTypeChartRef = useRef("feeTypeChartCanvas");
    this.gradeBandsChartRef = useRef("gradeBandsChartCanvas");

    this.charts = {};

    onWillStart(async () => {
      try {
        await loadBundle("web.chartjs_lib");
      } catch (err) {
        console.warn("Could not load chartjs_lib bundle:", err);
      }
      try {
        const isTeacher = await this.user.hasGroup("school_management.group_school_teacher");
        const isAdmin = await this.user.hasGroup("school_management.group_school_admin");
        const isStudent = await this.user.hasGroup("school_management.group_school_student");
        if (isStudent && !isTeacher && !isAdmin) {
          this.action.doAction("school_management.action_student", { clear_breadcrumbs: true });
          return;
        }
      } catch (err) {
        console.warn("Group check fallback in dashboard:", err);
      }
      await this.loadData();
    });

    useEffect(
      () => {
        if (!this.state.loading && this.state.data) {
          Promise.resolve().then(() => {
            if (!this.state.loading && this.state.data) {
              this.renderAllCharts();
            }
          });
        }
        return () => {
          this.destroyAllCharts();
        };
      },
      () => [this.state.loading, this.state.data]
    );
  }

  async loadData() {
    this.state.loading = true;
    try {
      const data = await this.orm.call(
        "school.dashboard",
        "get_dashboard_data",
        [],
      );
      this.state.data = data;
      this.state.lastUpdated = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch (error) {
      console.error("Failed to load school dashboard data:", error);
      this.action.doAction("school_management.action_student", { clear_breadcrumbs: true });
    } finally {
      this.state.loading = false;
    }
  }

  async onRefresh() {
    await this.loadData();
  }

  // ---------------- Navigation Actions ----------------
  openStudents(domain = []) {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Students",
      res_model: "school.student",
      views: [
        [false, "kanban"],
        [false, "list"],
        [false, "form"],
      ],
      domain: domain,
      context: domain.length ? { search_default_studying: 0 } : {},
    });
  }

  openTeachers(domain = []) {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Teachers",
      res_model: "school.teacher",
      views: [
        [false, "kanban"],
        [false, "list"],
        [false, "form"],
      ],
      domain: domain,
    });
  }

  openClasses(domain = []) {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Classes",
      res_model: "school.class",
      views: [
        [false, "list"],
        [false, "form"],
      ],
      domain: domain,
    });
  }

  openSubjects(domain = []) {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Subjects",
      res_model: "school.subject",
      views: [
        [false, "list"],
        [false, "form"],
      ],
      domain: domain,
    });
  }

  openExams(domain = []) {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Exams",
      res_model: "school.exam",
      views: [
        [false, "list"],
        [false, "form"],
      ],
      domain: domain,
    });
  }

  openGrades(domain = []) {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Grades",
      res_model: "school.grade",
      views: [
        [false, "list"],
        [false, "form"],
      ],
      domain: domain,
    });
  }

  openAttendance(domain = []) {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Attendance",
      res_model: "school.attendance",
      views: [
        [false, "list"],
        [false, "form"],
      ],
      domain: domain,
    });
  }

  openFees(domain = []) {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Fees",
      res_model: "school.fee",
      views: [
        [false, "list"],
        [false, "form"],
      ],
      domain: domain,
    });
  }

  openPermissions(domain = []) {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Student & Faculty Permissions",
      res_model: "school.permission",
      views: [
        [false, "list"],
        [false, "form"],
      ],
      domain: domain,
    });
  }

  openFeedback(domain = []) {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Teaching Reports & Student Feedback",
      res_model: "school.feedback",
      views: [
        [false, "list"],
        [false, "kanban"],
        [false, "form"],
      ],
      domain: domain,
    });
  }

  openCertificates(domain = []) {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Transcripts & Certificates",
      res_model: "school.certificate",
      views: [
        [false, "list"],
        [false, "form"],
      ],
      domain: domain,
    });
  }

  openYearPayments(domain = []) {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Annual Tuition Schedules & Payments",
      res_model: "school.student.year.payment",
      views: [
        [false, "list"],
        [false, "form"],
      ],
      domain: domain,
    });
  }

  // ---------------- Chart Cleanup & Lifecycle ----------------
  destroyAllCharts() {
    Object.keys(this.charts).forEach((key) => {
      if (this.charts[key]) {
        try {
          this.charts[key].destroy();
        } catch (e) {
          console.warn("Chart destroy warning:", key, e);
        }
        this.charts[key] = null;
      }
    });
  }

  _safeGetOrCreateCanvas(ref, ChartClass) {
    if (!ref || !ref.el) return null;
    try {
      const existing = ChartClass.getChart ? ChartClass.getChart(ref.el) : null;
      if (existing) {
        existing.destroy();
      }
    } catch (e) {
      console.warn("Canvas reset warning:", e);
    }
    return ref.el;
  }

  // ---------------- Visual Charts Rendering ----------------
  renderAllCharts() {
    this.destroyAllCharts();
    const ChartClass = window.Chart || (typeof Chart !== "undefined" ? Chart : null);
    if (!ChartClass || !this.state.data) {
      return;
    }

    const { demographics, attendance, fees, academics } = this.state.data;

    // 1. Gender Demographics
    try {
      const totalGender = (demographics.male || 0) + (demographics.female || 0) + (demographics.other || 0);
      const canvas = this._safeGetOrCreateCanvas(this.genderChartRef, ChartClass);
      if (canvas && totalGender > 0) {
        this.charts.gender = new ChartClass(canvas, {
          type: "doughnut",
          data: {
            labels: ["Male", "Female", "Other"],
            datasets: [
              {
                data: [
                  demographics.male,
                  demographics.female,
                  demographics.other,
                ],
                backgroundColor: ["#0891b2", "#2563eb", "#7c3aed"],
                borderWidth: 2,
                borderColor: "#ffffff",
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: "bottom",
                labels: { boxWidth: 12, padding: 12 },
              },
            },
            cutout: "68%",
          },
        });
      }
    } catch (e) {
      console.error("Failed to render gender chart:", e);
    }

    // 2. Attendance Status
    try {
      const totalAtt = (attendance.present || 0) + (attendance.late || 0) + (attendance.excused || 0) + (attendance.absent || 0);
      const canvas = this._safeGetOrCreateCanvas(this.attendanceChartRef, ChartClass);
      if (canvas && totalAtt > 0) {
        this.charts.attendance = new ChartClass(canvas, {
          type: "doughnut",
          data: {
            labels: ["Present", "Late", "Excused", "Absent"],
            datasets: [
              {
                data: [
                  attendance.present,
                  attendance.late,
                  attendance.excused,
                  attendance.absent,
                ],
                backgroundColor: ["#10b981", "#d97706", "#0891b2", "#ef4444"],
                borderWidth: 2,
                borderColor: "#ffffff",
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: "bottom",
                labels: { boxWidth: 12, padding: 12 },
              },
            },
            cutout: "68%",
          },
        });
      }
    } catch (e) {
      console.error("Failed to render attendance chart:", e);
    }

    // 3. Attendance Monthly Trend
    try {
      const canvas = this._safeGetOrCreateCanvas(this.attendanceTrendChartRef, ChartClass);
      if (canvas && attendance.trend && attendance.trend.length) {
        const labels = attendance.trend.map((t) => t.label);
        const rates = attendance.trend.map((t) => t.rate);

        this.charts.trend = new ChartClass(canvas, {
          type: "line",
          data: {
            labels: labels,
            datasets: [
              {
                label: "Attendance Rate (%)",
                data: rates,
                borderColor: "#0f766e",
                backgroundColor: "rgba(15, 118, 110, 0.08)",
                fill: true,
                tension: 0.35,
                pointBackgroundColor: "#0f766e",
                pointBorderColor: "#ffffff",
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                min: 0,
                max: 100,
                ticks: { callback: (v) => `${v}%`, stepSize: 20 },
                grid: { color: "#f1f5f9" },
              },
              x: {
                grid: { display: false },
              },
            },
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: (ctx) => ` Attendance: ${ctx.parsed.y}%`,
                },
              },
            },
          },
        });
      }
    } catch (e) {
      console.error("Failed to render trend chart:", e);
    }

    // 4. Fee Status
    try {
      const totalFee = (fees.paid_count || 0) + (fees.partial_count || 0) + (fees.pending_count || 0) + (fees.overdue_count || 0);
      const canvas = this._safeGetOrCreateCanvas(this.feeStatusChartRef, ChartClass);
      if (canvas && totalFee > 0) {
        this.charts.feeStatus = new ChartClass(canvas, {
          type: "doughnut",
          data: {
            labels: ["Paid", "Partial", "Pending", "Overdue"],
            datasets: [
              {
                data: [
                  fees.paid_count,
                  fees.partial_count,
                  fees.pending_count,
                  fees.overdue_count,
                ],
                backgroundColor: ["#10b981", "#2563eb", "#d97706", "#ef4444"],
                borderWidth: 2,
                borderColor: "#ffffff",
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: "bottom",
                labels: { boxWidth: 12, padding: 12 },
              },
            },
            cutout: "68%",
          },
        });
      }
    } catch (e) {
      console.error("Failed to render fee status chart:", e);
    }

    // 5. Fee Type Breakdown
    try {
      const canvas = this._safeGetOrCreateCanvas(this.feeTypeChartRef, ChartClass);
      if (canvas && fees.types && fees.types.length) {
        const labels = fees.types.map((t) => t.label);
        const billed = fees.types.map((t) => t.billed);
        const collected = fees.types.map((t) => t.collected);

        this.charts.feeType = new ChartClass(canvas, {
          type: "bar",
          data: {
            labels: labels,
            datasets: [
              {
                label: "Billed ($)",
                data: billed,
                backgroundColor: "#64748b",
                borderRadius: 4,
              },
              {
                label: "Collected ($)",
                data: collected,
                backgroundColor: "#0f766e",
                borderRadius: 4,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                beginAtZero: true,
                grid: { color: "#f1f5f9" },
              },
              x: {
                grid: { display: false },
              },
            },
            plugins: {
              legend: { position: "top", labels: { boxWidth: 12 } },
            },
          },
        });
      }
    } catch (e) {
      console.error("Failed to render fee type chart:", e);
    }

    // 6. Grade Bands
    try {
      const canvas = this._safeGetOrCreateCanvas(this.gradeBandsChartRef, ChartClass);
      if (canvas && academics.grade_bands && academics.grade_bands.length) {
        const labels = academics.grade_bands.map((b) => b.letter);
        const counts = academics.grade_bands.map((b) => b.count);
        const colors = academics.grade_bands.map((b) => b.color);

        this.charts.gradeBands = new ChartClass(canvas, {
          type: "bar",
          data: {
            labels: labels,
            datasets: [
              {
                label: "Students",
                data: counts,
                backgroundColor: colors,
                borderRadius: 4,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                beginAtZero: true,
                ticks: { precision: 0 },
                grid: { color: "#f1f5f9" },
              },
              x: {
                grid: { display: false },
              },
            },
            plugins: {
              legend: { display: false },
            },
          },
        });
      }
    } catch (e) {
      console.error("Failed to render grade bands chart:", e);
    }
  }

  formatCurrency(val) {
    if (!val && val !== 0) return "$0.00";
    return (
      "$" +
      Number(val).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    );
  }
}

registry.category("actions").add("school_dashboard", SchoolDashboard);

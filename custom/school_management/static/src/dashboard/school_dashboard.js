/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { Component, onWillStart, useEffect, useRef, useState } from "@odoo/owl";

export class SchoolDashboard extends Component {
  static template = "school_management.SchoolDashboardMain";
  static props = ["*"];

  setup() {
    super.setup();
    this.orm = useService("orm");
    this.action = useService("action");

    this.state = useState({
      loading: true,
      data: null,
      lastUpdated: new Date().toLocaleTimeString(),
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
        console.warn("Could not load chartjs_lib bundle", err);
      }
      await this.loadData();
    });

    useEffect(() => {
      if (!this.state.loading && this.state.data) {
        this.renderAllCharts();
      }
      return () => {
        this.destroyAllCharts();
      };
    });
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
      this.state.lastUpdated = new Date().toLocaleTimeString();
    } catch (error) {
      console.error("Failed to load school dashboard data:", error);
    } finally {
      this.state.loading = false;
    }
  }

  async onRefresh() {
    await this.loadData();
  }

  openStudents(domain = []) {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Students",
      res_model: "school.student",
      views: [
        [false, "list"],
        [false, "form"],
      ],
      domain: domain,
    });
  }

  openTeachers() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Teachers",
      res_model: "school.teacher",
      views: [
        [false, "list"],
        [false, "form"],
      ],
    });
  }

  openClasses() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Classes",
      res_model: "school.class",
      views: [
        [false, "list"],
        [false, "form"],
      ],
    });
  }

  openSubjects() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Subjects",
      res_model: "school.subject",
      views: [
        [false, "list"],
        [false, "form"],
      ],
    });
  }

  openExams() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Exams",
      res_model: "school.exam",
      views: [
        [false, "list"],
        [false, "form"],
      ],
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

  destroyAllCharts() {
    Object.keys(this.charts).forEach((key) => {
      if (this.charts[key]) {
        try {
          this.charts[key].destroy();
        } catch (e) {}
        this.charts[key] = null;
      }
    });
  }

  renderAllCharts() {
    this.destroyAllCharts();
    const ChartClass = window.Chart;
    if (!ChartClass || !this.state.data) {
      return;
    }

    const { demographics, attendance, fees, academics } = this.state.data;

    // 1. Gender Demographics
    if (this.genderChartRef.el) {
      this.charts.gender = new ChartClass(this.genderChartRef.el, {
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

    // 2. Attendance Status
    if (this.attendanceChartRef.el) {
      this.charts.attendance = new ChartClass(this.attendanceChartRef.el, {
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

    // 3. Attendance Monthly Trend
    if (
      this.attendanceTrendChartRef.el &&
      attendance.trend &&
      attendance.trend.length
    ) {
      const labels = attendance.trend.map((t) => t.label);
      const rates = attendance.trend.map((t) => t.rate);

      this.charts.trend = new ChartClass(this.attendanceTrendChartRef.el, {
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

    // 4. Fee Status
    if (this.feeStatusChartRef.el) {
      this.charts.feeStatus = new ChartClass(this.feeStatusChartRef.el, {
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

    // 5. Fee Type
    if (this.feeTypeChartRef.el && fees.types && fees.types.length) {
      const labels = fees.types.map((t) => t.label);
      const billed = fees.types.map((t) => t.billed);
      const collected = fees.types.map((t) => t.collected);

      this.charts.feeType = new ChartClass(this.feeTypeChartRef.el, {
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

    // 6. Grade Bands
    if (
      this.gradeBandsChartRef.el &&
      academics.grade_bands &&
      academics.grade_bands.length
    ) {
      const labels = academics.grade_bands.map((b) => b.letter);
      const counts = academics.grade_bands.map((b) => b.count);
      const colors = academics.grade_bands.map((b) => b.color);

      this.charts.gradeBands = new ChartClass(this.gradeBandsChartRef.el, {
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

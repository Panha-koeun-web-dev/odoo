/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CalendarController } from "@web/views/calendar/calendar_controller";

patch(CalendarController.prototype, {
    get isSchoolTimetable() {
        return this.props.resModel === "school.timetable";
    },

    onCalendarTitleClick() {
        if (this.isSchoolTimetable) {
            const currentWeekNum = this.currentWeek ? String(this.currentWeek) : "41";
            this.action.doAction("school_management.action_school_timetable_week_selector", {
                additionalContext: {
                    default_week_number: currentWeekNum,
                    default_term_id: this.props.context?.default_term_id || false,
                    default_class_id: this.props.context?.default_class_id || false,
                    default_teacher_id: this.props.context?.default_teacher_id || false,
                },
            });
        }
    },

    async onSchoolTimetableTodayClick() {
        await this.setDate("today");
        if (!this.isSchoolTimetable || !this.env.searchModel) {
            return;
        }

        // Week filters remain selected when navigating around the calendar. Clear
        // those stale filters so they cannot hide the week we just navigated to.
        const searchModel = this.env.searchModel;
        const activeWeekFilters = searchModel.query
            .map((queryItem) => searchModel.searchItems[queryItem.searchItemId])
            .filter((item) => item?.type === "filter" && /^filter_week_\d+$/.test(item.name));
        for (const filter of activeWeekFilters) {
            searchModel.toggleSearchItem(filter.id);
        }

        const currentWeek = this.model.rangeStart.weekNumber;
        const currentWeekFilter = Object.values(searchModel.searchItems).find(
            (item) => item.type === "filter" && item.name === `filter_week_${currentWeek}`
        );
        if (currentWeekFilter && !searchModel.query.some((item) => item.searchItemId === currentWeekFilter.id)) {
            searchModel.toggleSearchItem(currentWeekFilter.id);
        }
    },
});

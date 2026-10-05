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
});

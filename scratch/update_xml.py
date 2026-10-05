with open('custom/school_management/views/timetable_views.xml', 'r', encoding='utf-8') as f:
    xml = f.read()

# 1. Clean calendar view fields
cal_old = """                <field name="time_display"/>
                <field name="term_id" invisible="1"/>
                <field name="day_of_week" invisible="1"/>
                <field name="period" invisible="1"/>
                <field name="subject_id" invisible="1"/>
                <field name="student_id" invisible="1"/>"""

cal_new = """                <field name="time_display"/>
                <field name="term_id" invisible="1"/>
                <field name="day_of_week" invisible="1"/>
                <field name="period" invisible="1"/>
                <field name="student_id" invisible="1"/>"""

if cal_old in xml:
    xml = xml.replace(cal_old, cal_new, 1)
    print("Cleaned up calendar view fields")

# 2. Update action_timetable
act1_old = """    <record id="action_timetable" model="ir.actions.act_window">
        <field name="name">Master Timetable &amp; Schedules</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">list,calendar,kanban,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_filter_mon_fri': 1}</field>"""

act1_new = """    <record id="action_timetable" model="ir.actions.act_window">
        <field name="name">Master Timetable &amp; Schedules</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">calendar,kanban,list,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_filter_active_term': 1, 'search_default_filter_mon_fri': 1}</field>"""

if act1_old in xml:
    xml = xml.replace(act1_old, act1_new, 1)
    print("Updated action_timetable")

# 3. Update action_school_timetable
act2_old = """    <record id="action_school_timetable" model="ir.actions.act_window">
        <field name="name">Timetable &amp; Schedule</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">list,calendar,kanban,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_filter_mon_fri': 1}</field>"""

act2_new = """    <record id="action_school_timetable" model="ir.actions.act_window">
        <field name="name">Timetable &amp; Schedule</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">calendar,kanban,list,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_filter_active_term': 1, 'search_default_filter_mon_fri': 1}</field>"""

if act2_old in xml:
    xml = xml.replace(act2_old, act2_new, 1)
    print("Updated action_school_timetable")

# 4. Update action_timetable_teacher
act3_old = """    <record id="action_timetable_teacher" model="ir.actions.act_window">
        <field name="name">Teacher Teaching Schedules</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">list,calendar,kanban,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_group_teacher': 1}</field>"""

act3_new = """    <record id="action_timetable_teacher" model="ir.actions.act_window">
        <field name="name">Teacher Teaching Schedules</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">list,calendar,kanban,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_filter_active_term': 1, 'search_default_group_teacher': 1}</field>"""

if act3_old in xml:
    xml = xml.replace(act3_old, act3_new, 1)
    print("Updated action_timetable_teacher")

# 5. Update action_timetable_student
act4_old = """    <record id="action_timetable_student" model="ir.actions.act_window">
        <field name="name">Student Study Schedules</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">list,calendar,kanban,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_filter_mon_fri': 1, 'search_default_group_class': 1}</field>"""

act4_new = """    <record id="action_timetable_student" model="ir.actions.act_window">
        <field name="name">Student Study Schedules</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">list,calendar,kanban,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_filter_active_term': 1, 'search_default_filter_mon_fri': 1, 'search_default_group_class': 1}</field>"""

if act4_old in xml:
    xml = xml.replace(act4_old, act4_new, 1)
    print("Updated action_timetable_student")

# 6. Update action_timetable_my_teaching
act5_old = """    <record id="action_timetable_my_teaching" model="ir.actions.act_window">
        <field name="name">My Teaching Schedule</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">calendar,list,kanban,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_filter_my_teaching': 1, 'search_default_filter_mon_fri': 1}</field>"""

act5_new = """    <record id="action_timetable_my_teaching" model="ir.actions.act_window">
        <field name="name">My Teaching Schedule</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">calendar,list,kanban,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_filter_active_term': 1, 'search_default_filter_my_teaching': 1, 'search_default_filter_mon_fri': 1}</field>"""

if act5_old in xml:
    xml = xml.replace(act5_old, act5_new, 1)
    print("Updated action_timetable_my_teaching")

# 7. Update action_timetable_my_class
act6_old = """    <record id="action_timetable_my_class" model="ir.actions.act_window">
        <field name="name">My Class Timetable &amp; Calendar</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">calendar,list,kanban,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_filter_my_class': 1, 'search_default_filter_mon_fri': 1}</field>"""

act6_new = """    <record id="action_timetable_my_class" model="ir.actions.act_window">
        <field name="name">My Class Timetable &amp; Calendar</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">calendar,list,kanban,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_filter_active_term': 1, 'search_default_filter_my_class': 1, 'search_default_filter_mon_fri': 1}</field>"""

if act6_old in xml:
    xml = xml.replace(act6_old, act6_new, 1)
    print("Updated action_timetable_my_class")

# 8. Update action_school_my_timetable
act7_old = """    <record id="action_school_my_timetable" model="ir.actions.act_window">
        <field name="name">My Schedule</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">calendar,list,kanban,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_filter_my_schedule': 1, 'search_default_filter_mon_fri': 1}</field>"""

act7_new = """    <record id="action_school_my_timetable" model="ir.actions.act_window">
        <field name="name">My Schedule</field>
        <field name="res_model">school.timetable</field>
        <field name="view_mode">calendar,list,kanban,form</field>
        <field name="search_view_id" ref="view_school_timetable_search"/>
        <field name="context">{'search_default_filter_active_term': 1, 'search_default_filter_my_schedule': 1, 'search_default_filter_mon_fri': 1}</field>"""

if act7_old in xml:
    xml = xml.replace(act7_old, act7_new, 1)
    print("Updated action_school_my_timetable")

# 9. Add server action for master timetable
server_act = """
    <!-- Server Action to open Master Timetable dynamically anchored to Active Term -->
    <record id="action_server_master_timetable" model="ir.actions.server">
        <field name="name">Master Timetable &amp; Schedules</field>
        <field name="model_id" ref="model_school_timetable"/>
        <field name="state">code</field>
        <field name="code">
action = model.action_open_master_timetable()
        </field>
    </record>
"""
if 'id="action_server_master_timetable"' not in xml:
    idx = xml.rfind('</odoo>')
    xml = xml[:idx] + server_act + '\n</odoo>'
    print("Added action_server_master_timetable to timetable_views.xml")

with open('custom/school_management/views/timetable_views.xml', 'w', encoding='utf-8') as f:
    f.write(xml)

# 10. Update menu.xml to point to action_server_master_timetable
with open('custom/school_management/views/menu.xml', 'r', encoding='utf-8') as f:
    m_xml = f.read()

old_menu = """    <!-- 4A. Unified Timetable & Master Calendar -->
    <menuitem id="menu_school_sched_master"
              name="Timetable &amp; Master Calendar"
              parent="menu_school_schedule_root"
              action="action_timetable"
              groups="school_management.group_school_admin,school_management.group_school_teacher,school_management.group_school_student"
              sequence="5"/>"""

new_menu = """    <!-- 4A. Unified Timetable & Master Calendar -->
    <menuitem id="menu_school_sched_master"
              name="Timetable &amp; Master Calendar"
              parent="menu_school_schedule_root"
              action="action_server_master_timetable"
              groups="school_management.group_school_admin,school_management.group_school_teacher,school_management.group_school_student"
              sequence="5"/>"""

if old_menu in m_xml:
    m_xml = m_xml.replace(old_menu, new_menu, 1)
    print("Updated menu_school_sched_master to action_server_master_timetable")
    with open('custom/school_management/views/menu.xml', 'w', encoding='utf-8') as f:
        f.write(m_xml)

print("XML updates complete.")

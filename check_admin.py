from lxml import etree
tree = etree.parse('custom/school_management/security/school_security.xml')
root = tree.getroot()

# Check admin group
admin_group = root.find(".//record[@id='group_school_admin']")
if admin_group is not None:
    name = admin_group.find("field[@name='name']").text
    implied = admin_group.find("field[@name='implied_ids']").get('eval')
    user_ids = admin_group.find("field[@name='user_ids']").get('eval')
    print(f"Group: {name}")
    print(f"Implied IDs: {implied}")
    print(f"User IDs: {user_ids}")
else:
    print("Admin group not found")
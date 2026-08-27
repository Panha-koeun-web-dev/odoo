# School Management System - Run Guide

Your Odoo server is already running on port 8069. Follow these steps:

---

## Step 1: Open Browser

Go to: **http://localhost:8069**

---

## Step 2: Login

- Database: **testing_db**
- Email: **admin**
- Password: **admin**

---

## Step 3: Activate the Module

1. Click **Apps** in the top menu
2. In the search bar, delete **Apps** filter (click the X)
3. Type **school_management** in the search box
4. You will see **School Management** card
5. Click **Activate** button (this = Install)
6. Wait for the page to reload

---

## Step 4: Use the Module

After activation, a new **School** menu appears in the top navigation bar.

Click **School** to see:
- **Students** → Add/edit student records
- **Teachers** → Add/edit teacher records
- **Classes** → Manage classes
- **Subjects** → Manage subjects
- **Attendance** → Track daily attendance
- **Exams** → Create exams
- **Grades** → Enter student grades
- **Fees** → Manage fee payments

---

## Step 5: Add Test Data

1. Go to **School → Subjects** → Click **New** → Add "Mathematics"
2. Go to **School → Teachers** → Click **New** → Add a teacher
3. Go to **School → Classes** → Click **New** → Create "Grade 10" section A
4. Go to **School → Students** → Click **New** → Add a student and assign to Grade 10

---

## Quick Command (Alternative)

If the module doesn't appear, run this in terminal to force install:

```powershell
cd C:\Users\USER\Desktop\odoo
python odoo-bin -c odoo.conf -d testing_db -i school_management --stop-after-init
```

Then start the server again:

```powershell
cd C:\Users\USER\Desktop\odoo
python odoo-bin -c odoo.conf
```

Open **http://localhost:8069** and repeat from Step 2.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Page doesn't load | Check Odoo server is running (port 8069) |
| Can't login | Use `admin` / `admin` |
| School menu not showing | Module not activated yet, go back to Step 3 |
| Error on activate | Check the terminal where Odoo is running for error messages |

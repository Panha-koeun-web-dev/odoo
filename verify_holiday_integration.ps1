# PowerShell script to verify holiday integration with school management

Write-Host "=== Odoo School Holiday Integration Verification ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check holidays in Odoo
Write-Host "Step 1: Verify imported holidays" -ForegroundColor Yellow
Write-Host "1. Navigate to: School → Public Holidays"
Write-Host "2. Count the number of holidays imported"
Write-Host "3. Verify each holiday has 'National Holiday' in Holiday Type field"
Write-Host ""

# Step 2: Check timetable integration
Write-Host "Step 2: Verify timetable integration" -ForegroundColor Yellow
Write-Host "1. Navigate to: School → Timetable → Calendar view"
Write-Host "2. Check the calendar date range"
Write-Host "3. Verify holiday dates are marked with holiday banners"
Write-Host "4. Look for the holiday name labels on the calendar"
Write-Host ""

# Step 3: Test conflict prevention
Write-Host "Step 3: Test conflict prevention" -ForegroundColor Yellow
Write-Host "1. Try to create a new timetable session on a holiday date"
Write-Host "2. System should show: Validation Error"
Write-Host "   'Cannot schedule class session on [date]: Public Holiday [name] is active on this day.'"
Write-Host "   No regular classes allowed on public holidays"
Write-Host ""

# Step 4: Test auto-reschedule (if holidays existed before sessions)
Write-Host "Step 4: Verify auto-reschedule functionality" -ForegroundColor Yellow
Write-Host "1. If you had existing timetable sessions on holiday dates,"
Write-Host "   they should have been automatically moved to next week"
Write-Host "2. Check the moved sessions in the timetable list view"
Write-Host ""

# Step 5: Verify specific holiday dates
Write-Host "Step 5: Verify specific Cambodia holidays" -ForegroundColor Yellow
Write-Host "1. Khmer New Year (2026-04-14 to 2026-04-16): Should be marked as holiday"
Write-Host "2. Water Festival (2026-11-23 to 2026-11-25): Should be marked as holiday"
Write-Host "3. Christmas (2026-12-25): Should be marked as holiday"
Write-Host "2027 dates similarly"
Write-Host ""

Write-Host "=== Verification Complete ===" -ForegroundColor Cyan
Write-Host "If all checks pass, your public holidays integrate successfully!"
Write-Host "with the school management timetable module."
# TVS TCMS Mobile Testing Guide
**Date:** April 1, 2026
**Purpose:** Verify mobile responsiveness fixes work correctly on all target devices

---

## TESTING DEVICES

Test at these exact widths using browser DevTools:
- **375px** - iPhone SE (smallest modern iPhone)
- **390px** - iPhone 14 (most common)
- **414px** - iPhone 14 Plus (large iPhone)
- **360px** - Android (common Android width)

---

## CRITICAL FIXES IMPLEMENTED

### ✅ FIX 1: Column Classes (ALL PAGES)
**What was fixed:** Added `col-12` to all `col-md-*` elements so they stack properly on mobile

**Files changed:**
- `wages.html` - Summary cards now stack
- `expenses.html` - Summary cards and filters now stack
- `runsheets.html` - Filter dropdowns now stack
- `settings/profile.html` - Form fields now full-width

**Test:**
1. Open each page on 375px width
2. Verify summary cards are full-width and stacked vertically
3. Verify filter dropdowns are full-width and stacked
4. Verify form fields are full-width

**Expected:** No horizontal scrolling, all elements full-width and readable

---

### ✅ FIX 2: Navbar Dropdowns
**What was fixed:** Mobile-optimized dropdown menus with larger touch targets

**Test:**
1. Open any page on 390px width
2. Tap hamburger menu (should open smoothly)
3. Tap "Wages" dropdown
4. Tap "Settings" dropdown
5. Tap username dropdown

**Expected:**
- Dropdowns open full-width below nav item
- Touch targets minimum 44px height
- Easy to tap without mis-taps
- Active items highlighted with blue background

---

### ✅ FIX 3: Search Modal
**What was fixed:** Modal is now full-screen on mobile devices

**Test:**
1. Open any page on 375px width
2. Tap "Search" in navbar
3. Modal should fill entire screen
4. Try typing in search box
5. Close modal

**Expected:**
- Modal covers entire screen (no margins)
- Search input doesn't zoom on focus
- Easy to close with X button
- Keyboard doesn't cover input

---

### ✅ FIX 4: Button Layouts
**What was fixed:** Expense page buttons now horizontal scroll instead of huge vertical stack

**Test:**
1. Open Expenses page on 390px width
2. Look at button row below page header
3. Swipe left/right on buttons

**Expected:**
- Buttons in horizontal scrollable row
- Each button readable and tappable
- Smooth scroll with momentum
- No vertical space wasted

---

### ✅ FIX 5: Tab Navigation
**What was fixed:** Tabs now scroll horizontally on mobile

**Test:**
1. Open Run Sheets page on 375px width
2. Look at tab navigation (All Run Sheets, Overview, Customers, Activities)
3. Swipe left/right on tabs

**Expected:**
- Tabs scroll horizontally
- Active tab visible
- Smooth scrolling
- Scrollbar visible at bottom

---

### ✅ FIX 6: Tables
**What was fixed:** Tables have horizontal scroll with visual indicators

**Test:**
1. Open Run Sheets page on 390px width
2. Switch to desktop view (if mobile cards showing)
3. Scroll table horizontally

**Expected:**
- Table scrolls smoothly
- Shadow indicator on right edge
- All columns accessible
- Sticky header (if implemented)

---

### ✅ FIX 7: Forms
**What was fixed:** All form inputs are touch-friendly and don't zoom on focus

**Test:**
1. Open Settings > Profile on 375px width
2. Tap each input field
3. Type in each field

**Expected:**
- Inputs don't zoom when tapped
- Keyboard doesn't cover input
- Labels above inputs (not beside)
- Easy to tap and type

---

## COMPREHENSIVE PAGE TESTING

### 1. RUN SHEETS PAGE (MOST CRITICAL)

**Test at 375px:**
- [ ] Summary cards stack vertically
- [ ] Filter dropdowns full-width and stacked
- [ ] Tabs scroll horizontally
- [ ] Mobile card view shows (not table)
- [ ] Cards are readable and tappable
- [ ] Pagination works
- [ ] Can view job details

**Test at 390px:**
- [ ] Same as above
- [ ] Charts resize properly
- [ ] Overview tab works

**Test at 414px:**
- [ ] Layout looks good (not too stretched)
- [ ] All features accessible

---

### 2. WAGES PAGE

**Test at 375px:**
- [ ] Summary cards stack vertically
- [ ] "Add Verbal Confirmation" button full-width
- [ ] Tabs scroll horizontally
- [ ] Payslip list readable
- [ ] Can view payslip details

**Test at 390px:**
- [ ] Charts display properly
- [ ] Job items list readable

---

### 3. EXPENSES PAGE

**Test at 375px:**
- [ ] Summary cards stack vertically
- [ ] Action buttons scroll horizontally
- [ ] Filter dropdowns stack vertically
- [ ] Can add expense (modal full-screen)
- [ ] Expense list readable
- [ ] Can edit/delete expenses

**Test at 390px:**
- [ ] Bank import modal works
- [ ] Recurring templates accessible

---

### 4. SETTINGS PAGES

**Test at 375px:**
- [ ] Profile: All form fields full-width
- [ ] Profile: Can save changes
- [ ] Profile: Password change works
- [ ] Sync: Controls accessible
- [ ] Attendance: Records display well
- [ ] System: All options accessible

---

### 5. NAVBAR & NAVIGATION

**Test at 375px:**
- [ ] Hamburger menu works
- [ ] All nav items accessible
- [ ] Dropdowns open properly
- [ ] Can navigate to all pages
- [ ] User menu works
- [ ] Logout works

**Test at 360px (narrowest):**
- [ ] Logo + brand text fit
- [ ] Hamburger doesn't overlap
- [ ] All features still work

---

## ORIENTATION TESTING

**Portrait Mode:**
- [ ] All pages work in portrait
- [ ] Scrolling smooth
- [ ] No horizontal scroll

**Landscape Mode:**
- [ ] Reduced vertical spacing
- [ ] Modals still usable
- [ ] Tables more usable
- [ ] No layout breaks

---

## TOUCH INTERACTION TESTING

**Tap Targets:**
- [ ] All buttons minimum 44px height
- [ ] Easy to tap without mis-taps
- [ ] No accidental taps on nearby elements

**Scrolling:**
- [ ] Smooth momentum scrolling
- [ ] No scroll jank
- [ ] Tables scroll horizontally
- [ ] Tabs scroll horizontally
- [ ] Page scrolls vertically

**Forms:**
- [ ] Inputs don't zoom on focus
- [ ] Keyboard doesn't cover inputs
- [ ] Can type easily
- [ ] Can submit forms

---

## PERFORMANCE TESTING

**Load Times:**
- [ ] Pages load quickly on 3G
- [ ] No layout shift on load
- [ ] Images load progressively

**Responsiveness:**
- [ ] Buttons respond immediately
- [ ] No lag when typing
- [ ] Smooth animations

---

## BROWSER TESTING

Test in these mobile browsers:
- [ ] Safari iOS (iPhone)
- [ ] Chrome iOS (iPhone)
- [ ] Chrome Android
- [ ] Samsung Internet (Android)

---

## COMMON ISSUES TO CHECK

**Horizontal Scroll:**
- [ ] No horizontal scrolling on any page
- [ ] Content fits within viewport
- [ ] No elements overflow

**Text Readability:**
- [ ] All text minimum 14px
- [ ] Headings properly sized
- [ ] Good contrast
- [ ] Line height comfortable

**Spacing:**
- [ ] Adequate padding around elements
- [ ] Cards have proper margins
- [ ] Buttons not cramped
- [ ] Forms have breathing room

**Safe Areas:**
- [ ] Content not hidden by iPhone notch
- [ ] Bottom navigation not hidden by home indicator
- [ ] Modals respect safe areas

---

## REGRESSION TESTING

After mobile fixes, verify desktop still works:
- [ ] Desktop layout not broken
- [ ] Responsive breakpoints work
- [ ] Tablet view (768px-991px) works
- [ ] Large desktop (1920px+) works

---

## SIGN-OFF CHECKLIST

Before marking mobile responsiveness as complete:

- [ ] All critical fixes tested on 4 device widths
- [ ] All pages tested (Run Sheets, Wages, Expenses, Settings)
- [ ] Navbar and navigation tested
- [ ] Forms tested (can add/edit data)
- [ ] Modals tested (full-screen on mobile)
- [ ] Tables tested (horizontal scroll works)
- [ ] No horizontal scrolling anywhere
- [ ] All touch targets minimum 44px
- [ ] Text readable on smallest device (375px)
- [ ] Owner can use app on-site without frustration

---

## KNOWN LIMITATIONS

Document any remaining issues:
- None currently - all critical fixes implemented

---

## FUTURE ENHANCEMENTS (NICE-TO-HAVE)

Not critical, but would improve mobile experience:
1. Bottom navigation bar for quick access
2. Swipe gestures (swipe to delete, swipe between tabs)
3. Pull-to-refresh on run sheets
4. Sticky table headers
5. Loading skeletons instead of spinners
6. Haptic feedback on button taps

---

## TESTING NOTES

**Date:** _____________
**Tester:** _____________
**Device:** _____________
**Browser:** _____________

**Issues Found:**
1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

**Overall Rating:** ☐ Pass  ☐ Fail  ☐ Needs Work

**Comments:**
_________________________________________________
_________________________________________________
_________________________________________________

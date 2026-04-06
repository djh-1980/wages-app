-- Expense categories for HMRC MTD compliance
-- All 27 current categories including EPOS-specific ones

-- Create expense_categories table
CREATE TABLE IF NOT EXISTS expense_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    hmrc_box TEXT NOT NULL,
    hmrc_box_number INTEGER,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert all expense categories (INSERT OR IGNORE for idempotency)
INSERT OR IGNORE INTO expense_categories (id, name, hmrc_box, description) VALUES
(1, 'Vehicle Costs', 'Vehicle costs', 'Van loan, insurance, tax, MOT, repairs, tyres'),
(2, 'Fuel', 'Vehicle costs', 'Fuel and oil for business vehicle'),
(3, 'Travel Costs', 'Travel costs', 'Parking, tolls, public transport'),
(4, 'Premises Costs', 'Premises costs', 'Rent, rates, power, insurance (if applicable)'),
(5, 'Admin Costs', 'Admin costs', 'Phone, internet, stationery, postage'),
(6, 'Advertising', 'Advertising', 'Marketing and advertising costs'),
(7, 'Interest', 'Interest', 'Bank and loan interest'),
(8, 'Financial Charges', 'Financial charges', 'Bank charges, card fees'),
(9, 'Professional Fees', 'Professional fees', 'Accountant, legal, subscriptions'),
(10, 'Depreciation', 'Depreciation', 'Equipment depreciation'),
(11, 'Other Expenses', 'Other expenses', 'Tools, clothing, training, software'),
(15, 'Home Office', 'Premises costs', 'Home office allowance (£6/week simplified or actual costs)'),
(4008, 'Materials & Stock', 'Cost of goods bought', 'Materials, windows, flashings, fixings, sealants for jobs'),
(4009, 'Vehicle Maintenance', 'Maintenance costs', 'Van servicing, MOT, repairs, tyres'),
(4010, 'Equipment Maintenance', 'Maintenance costs', 'Tool repairs and servicing'),
(4011, 'CIS Payments', 'CIS payments to subcontractors', 'Payments to CIS subcontractors'),
(4012, 'Van Finance/Lease', 'Motor expenses', 'Monthly van finance or lease payments'),
(4013, 'Vehicle Insurance', 'Motor expenses', 'Van/vehicle insurance premiums'),
(4014, 'Breakdown Cover', 'Motor expenses', 'AA/RAC or other breakdown cover'),
(4015, 'Server & Hosting', 'Admin costs', 'Server hosting, electricity and internet costs for business'),
(4016, 'AI & Subscriptions', 'Admin costs', 'AI tools, remote desktop software, diagnostic subscriptions, domain names and cloud services used for business'),
(4017, 'Protective Clothing & PPE', 'Admin costs', 'Hi-vis, steel toe caps, gloves, hard hat and other protective work wear required on customer sites'),
(4018, 'Office Supplies', 'Admin costs', 'Stationery, printer ink, paper and general office supplies'),
(4019, '3D Printing Materials', 'Cost of goods bought', 'Filament and materials for printing custom brackets, enclosures and cable management solutions for EPOS installations'),
(4020, 'Tools & Equipment', 'Admin costs', 'Screwdrivers, cable testers, laptops, diagnostic equipment and tools for EPOS installations under £1000'),
(4021, 'Professional Development', 'Admin costs', 'Training courses, certifications, industry memberships and technical reference materials for EPOS systems'),
(4022, 'Parts & Consumables', 'Cost of goods bought', 'Cables, connectors, small parts, thermal paper and consumables used in EPOS installations and repairs');

-- Create expenses table
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    receipt_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES expense_categories(id)
);

-- Create recurring templates table
CREATE TABLE IF NOT EXISTS recurring_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    expected_amount REAL NOT NULL,
    frequency TEXT NOT NULL,
    merchant_pattern TEXT NOT NULL,
    day_of_month INTEGER,
    is_active BOOLEAN DEFAULT 1,
    tolerance_amount REAL DEFAULT 5.0,
    auto_import BOOLEAN DEFAULT 0,
    next_expected_date TEXT,
    last_matched_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES expense_categories(id)
);

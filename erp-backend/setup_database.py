"""
Database Setup Script for COMPLETE ERP System
Creates all tables including new features for chatbot RAG integration
Updated to match actual database schema (includes manual changes)
"""

import sqlite3
import csv
import os
from datetime import datetime

# Database file path
DB_PATH = "erp_database.db"

def create_database():
    """Create SQLite database with ALL tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Drop existing tables
    tables_to_drop = [
        'reports', 'equipment', 'issues', 'timesheets', 
        'purchase_orders', 'suppliers', 'notifications', 
        'activity_logs', 'documents', 'tasks',
        'leave_requests', 'kpis', 'projects', 'employees', 'access_rules'
    ]
    
    for table in tables_to_drop:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    
    print("🗑️  Dropped existing tables")
    
    # =========================================================================
    # CORE TABLES
    # =========================================================================
    
    # Projects table
    # ✏️ MANUAL CHANGE: added assigned_employees column
    cursor.execute("""
        CREATE TABLE projects (
            project_id TEXT PRIMARY KEY,
            project_name TEXT NOT NULL,
            project_type TEXT,
            client_name TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            budget_eur REAL,
            actual_cost_eur REAL,
            completion_percentage INTEGER,
            location TEXT,
            project_manager_id TEXT,
            site_supervisor_id TEXT,
            description TEXT,
            assigned_employees TEXT DEFAULT ''
        )
    """)
    
    # Employees table
    # ✏️ MANUAL CHANGE: added password_hash and must_change_password columns
    cursor.execute("""
        CREATE TABLE employees (
            employee_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            phone TEXT,
            position TEXT,
            department TEXT,
            role TEXT NOT NULL CHECK(role IN ('ceo', 'manager', 'employee', 'rh')),
            hire_date TEXT,
            salary_eur REAL,
            manager_id TEXT,
            supervised_employees TEXT,
            assigned_projects TEXT,
            specialization TEXT,
            certifications TEXT,
            years_experience INTEGER,
            annual_leave_total INTEGER DEFAULT 30,
            annual_leave_taken INTEGER DEFAULT 0,
            sick_leave_taken INTEGER DEFAULT 0,
            other_leave_taken INTEGER DEFAULT 0,
            password_hash TEXT,
            must_change_password INTEGER DEFAULT 1,
            FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
        )
    """)
    
    # KPIs table
    cursor.execute("""
        CREATE TABLE kpis (
            kpi_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            project_name TEXT,
            kpi_date TEXT,
            budget_variance_percentage REAL,
            schedule_variance_days INTEGER,
            quality_score INTEGER,
            safety_incidents INTEGER,
            client_satisfaction_score REAL,
            team_productivity_percentage INTEGER,
            cost_performance_index REAL,
            schedule_performance_index REAL,
            risk_level TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(project_id)
        )
    """)
    
    # Access rules table
    cursor.execute("""
        CREATE TABLE access_rules (
            role TEXT PRIMARY KEY CHECK(role IN ('ceo', 'manager', 'employee', 'rh')),
            description TEXT,
            can_view_all_projects BOOLEAN,
            can_view_own_projects BOOLEAN,
            can_view_supervised_projects BOOLEAN,
            can_view_all_employees BOOLEAN,
            can_view_supervised_employees BOOLEAN,
            can_view_all_salaries BOOLEAN,
            can_view_own_salary BOOLEAN,
            can_view_supervised_salaries BOOLEAN,
            can_edit_projects BOOLEAN,
            can_create_projects BOOLEAN,
            can_approve_budgets BOOLEAN
        )
    """)
    
    # Leave requests table
    cursor.execute("""
        CREATE TABLE leave_requests (
            request_id TEXT PRIMARY KEY,
            employee_id TEXT NOT NULL,
            employee_name TEXT,
            leave_type TEXT CHECK(leave_type IN ('Annual', 'Sick', 'Personal', 'Maternity', 'Emergency')),
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_days INTEGER NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Approved', 'Rejected', 'Cancelled')),
            requested_date TEXT NOT NULL,
            reviewed_by TEXT,
            reviewed_date TEXT,
            review_comment TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (reviewed_by) REFERENCES employees(employee_id)
        )
    """)
    
    # =========================================================================
    # FEATURE 1: TASKS
    # =========================================================================
    
    cursor.execute("""
        CREATE TABLE tasks (
            task_id TEXT PRIMARY KEY,
            project_id TEXT,
            assigned_to TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High', 'Critical')),
            status TEXT DEFAULT 'Todo' CHECK(status IN ('Todo', 'In Progress', 'Done', 'Blocked', 'Cancelled')),
            due_date TEXT,
            created_by TEXT NOT NULL,
            created_date TEXT NOT NULL,
            completed_date TEXT,
            estimated_hours REAL,
            actual_hours REAL,
            FOREIGN KEY (project_id) REFERENCES projects(project_id),
            FOREIGN KEY (assigned_to) REFERENCES employees(employee_id),
            FOREIGN KEY (created_by) REFERENCES employees(employee_id)
        )
    """)
    
    # =========================================================================
    # FEATURE 2: DOCUMENTS
    # =========================================================================
    
    cursor.execute("""
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY,
            project_id TEXT,
            document_name TEXT NOT NULL,
            document_type TEXT CHECK(document_type IN ('Contract', 'Invoice', 'Report', 'Plan', 'Photo', 'Certificate', 'Other')),
            file_path TEXT NOT NULL,
            file_size INTEGER,
            uploaded_by TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            description TEXT,
            tags TEXT,
            version TEXT DEFAULT '1.0',
            FOREIGN KEY (project_id) REFERENCES projects(project_id),
            FOREIGN KEY (uploaded_by) REFERENCES employees(employee_id)
        )
    """)
    
    # =========================================================================
    # FEATURE 3: ACTIVITY LOGS
    # =========================================================================
    
    cursor.execute("""
        CREATE TABLE activity_logs (
            log_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            description TEXT,
            old_value TEXT,
            new_value TEXT,
            timestamp TEXT NOT NULL,
            ip_address TEXT,
            FOREIGN KEY (user_id) REFERENCES employees(employee_id)
        )
    """)
    
    # =========================================================================
    # FEATURE 4: NOTIFICATIONS
    # ✏️ MANUAL CHANGE: added notification_type, related_entity_type, related_entity_id
    # =========================================================================
    
    cursor.execute("""
        CREATE TABLE notifications (
            notification_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT CHECK(type IN ('Leave', 'Task', 'Budget', 'Deadline', 'Document', 'Issue', 'General')),
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            link TEXT,
            is_read BOOLEAN DEFAULT 0,
            priority TEXT DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High')),
            created_date TEXT NOT NULL,
            read_date TEXT,
            notification_type TEXT,
            related_entity_type TEXT,
            related_entity_id TEXT,
            FOREIGN KEY (user_id) REFERENCES employees(employee_id)
        )
    """)
    
    # =========================================================================
    # FEATURE 5: SUPPLIERS
    # =========================================================================
    
    cursor.execute("""
        CREATE TABLE suppliers (
            supplier_id TEXT PRIMARY KEY,
            supplier_name TEXT NOT NULL,
            contact_person TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            city TEXT,
            country TEXT DEFAULT 'Tunisia',
            category TEXT CHECK(category IN ('Materials', 'Equipment', 'Services', 'Subcontractor')),
            rating INTEGER CHECK(rating BETWEEN 1 AND 5),
            status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Inactive')),
            created_date TEXT,
            notes TEXT
        )
    """)
    
    # =========================================================================
    # FEATURE 6: PURCHASE ORDERS
    # =========================================================================
    
    cursor.execute("""
        CREATE TABLE purchase_orders (
            po_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            supplier_id TEXT NOT NULL,
            order_date TEXT NOT NULL,
            delivery_date TEXT,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'Draft' CHECK(status IN ('Draft', 'Sent', 'Confirmed', 'Delivered', 'Cancelled')),
            items TEXT,
            created_by TEXT NOT NULL,
            approved_by TEXT,
            notes TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(project_id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
            FOREIGN KEY (created_by) REFERENCES employees(employee_id),
            FOREIGN KEY (approved_by) REFERENCES employees(employee_id)
        )
    """)
    
    # =========================================================================
    # FEATURE 7: TIMESHEETS
    # =========================================================================
    
    cursor.execute("""
        CREATE TABLE timesheets (
            timesheet_id TEXT PRIMARY KEY,
            employee_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            date TEXT NOT NULL,
            hours_worked REAL NOT NULL,
            task_description TEXT,
            billable BOOLEAN DEFAULT 1,
            hourly_rate REAL,
            is_approved BOOLEAN DEFAULT 0,
            approved_by TEXT,
            approved_date TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (project_id) REFERENCES projects(project_id),
            FOREIGN KEY (approved_by) REFERENCES employees(employee_id)
        )
    """)
    
    # =========================================================================
    # FEATURE 8: ISSUES
    # =========================================================================
    
    cursor.execute("""
        CREATE TABLE issues (
            issue_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            reported_by TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            severity TEXT DEFAULT 'Medium' CHECK(severity IN ('Low', 'Medium', 'High', 'Critical')),
            category TEXT CHECK(category IN ('Safety', 'Quality', 'Delay', 'Budget', 'Technical', 'Other')),
            status TEXT DEFAULT 'Open' CHECK(status IN ('Open', 'In Progress', 'Resolved', 'Closed')),
            assigned_to TEXT,
            created_date TEXT NOT NULL,
            resolved_date TEXT,
            resolution_notes TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(project_id),
            FOREIGN KEY (reported_by) REFERENCES employees(employee_id),
            FOREIGN KEY (assigned_to) REFERENCES employees(employee_id)
        )
    """)
    
    # =========================================================================
    # FEATURE 9: EQUIPMENT
    # =========================================================================
    
    cursor.execute("""
        CREATE TABLE equipment (
            equipment_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT CHECK(category IN ('Vehicle', 'Tool', 'Machinery', 'Safety')),
            serial_number TEXT,
            status TEXT DEFAULT 'Available' CHECK(status IN ('Available', 'In Use', 'Maintenance', 'Broken', 'Retired')),
            current_project_id TEXT,
            assigned_to TEXT,
            location TEXT,
            purchase_date TEXT,
            purchase_value REAL,
            last_maintenance TEXT,
            next_maintenance TEXT,
            notes TEXT,
            FOREIGN KEY (current_project_id) REFERENCES projects(project_id),
            FOREIGN KEY (assigned_to) REFERENCES employees(employee_id)
        )
    """)
    
    # =========================================================================
    # FEATURE 10: REPORTS
    # ✏️ MANUAL CHANGE: completely restructured — new columns: title, filters,
    #    parameters, status, content | removed: format, recipients |
    #    renamed: generated_date (was generated_date in script, now generation_date)
    # =========================================================================
    
    cursor.execute("""
        CREATE TABLE reports (
            report_id TEXT PRIMARY KEY,
            report_type TEXT NOT NULL,
            title TEXT NOT NULL,
            period_start TEXT,
            period_end TEXT,
            generated_by TEXT,
            generation_date TEXT,
            file_path TEXT,
            filters TEXT DEFAULT '{}',
            parameters TEXT DEFAULT '{}',
            status TEXT DEFAULT 'Completed',
            content TEXT DEFAULT '',
            FOREIGN KEY (generated_by) REFERENCES employees(employee_id)
        )
    """)
    
    conn.commit()
    print("✅ All tables created successfully")
    return conn


def import_csv_to_table(conn, csv_file, table_name):
    """Import CSV file into SQLite table"""
    cursor = conn.cursor()
    
    if not os.path.exists(csv_file):
        print(f"⚠️  Warning: {csv_file} not found, skipping...")
        return
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        if not rows:
            print(f"⚠️  Warning: {csv_file} is empty")
            return
        
        columns = list(rows[0].keys())
        
        # For employees table, add leave tracking with smart calculation
        if table_name == 'employees':
            for row in rows:
                role = row.get('role', 'employee')
                years = int(row.get('years_experience', 0))
                
                if role in ['ceo', 'manager', 'rh']:
                    annual_leave = 35
                elif years >= 10:
                    annual_leave = 32
                elif years >= 5:
                    annual_leave = 28
                else:
                    annual_leave = 25
                
                row['annual_leave_total'] = annual_leave
                row['annual_leave_taken'] = 0
                row['sick_leave_taken'] = 0
                row['other_leave_taken'] = 0
                # password_hash and must_change_password will be NULL/default from DB
            
            columns.extend(['annual_leave_total', 'annual_leave_taken', 'sick_leave_taken', 'other_leave_taken'])
        
        placeholders = ','.join(['?' for _ in columns])
        columns_str = ','.join(columns)
        
        insert_query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        
        for row in rows:
            values = [row.get(col, None) if row.get(col, '') != '' else None for col in columns]
            cursor.execute(insert_query, values)
        
        conn.commit()
        print(f"✅ Imported {len(rows)} rows into {table_name}")


def main():
    """Main function to set up the complete database"""
    print("🚀 Starting COMPLETE ERP database setup...")
    print("   Includes all manual schema changes\n")
    
    # Create database and tables
    conn = create_database()
    
    # Import CSV files
    print("\n📥 Importing CSV files...")
    import_csv_to_table(conn, 'projets.csv', 'projects')
    import_csv_to_table(conn, 'employes_final.csv', 'employees')
    import_csv_to_table(conn, 'kpis_projets.csv', 'kpis')
    import_csv_to_table(conn, 'access_rules.csv', 'access_rules')
    
    # Optional CSVs
    import_csv_to_table(conn, 'tasks.csv', 'tasks')
    import_csv_to_table(conn, 'documents.csv', 'documents')
    import_csv_to_table(conn, 'suppliers.csv', 'suppliers')
    import_csv_to_table(conn, 'equipment.csv', 'equipment')
    
    # Verify data
    cursor = conn.cursor()
    
    tables = [
        'projects', 'employees', 'kpis', 'access_rules', 'leave_requests',
        'tasks', 'documents', 'activity_logs', 'notifications', 'suppliers',
        'purchase_orders', 'timesheets', 'issues', 'equipment', 'reports'
    ]
    
    print(f"\n📊 Database Summary:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   {table:25} {count:>5} rows")
    
    conn.close()
    print(f"\n✅ ERP database created: {DB_PATH}")
    print("🤖 Ready for chatbot RAG integration!")


if __name__ == "__main__":
    main()
Order Management System
Project Description:

This is a full-featured, modern Order Management System built with Flask, designed to help small businesses, shops, and individuals effectively manage orders, payments, deliveries, and financial insights.

Key features include:

Order Tracking: Add, edit, and view orders with details such as platform, product, payment mode, spend, profit/loss, delivery status, and customer contact.

EMI Reminders: Smart automated reminders for EMI payment modes, calculated using working days (excluding weekends and Indian public holidays via live API).

Delivery Management: Mark orders as delivered or pending, update statuses, and record delivery dates.

File Management: Upload and organize order-related files (screenshots, PDFs), with backup integration for Google Drive via rclone.

Analytics Dashboard: View monthly/yearly spending, cash flow, and owner/category breakdowns with interactive charts.

Secure Login: Session-based login for secure access and privacy.

Mobile-Friendly UI: Responsive design for desktop and mobile.

Technology Stack:

Python (Flask)

HTML/CSS/JavaScript (Bootstrap, Chart.js, DataTables)

Google Drive/Cloud backup (via rclone)

Calendarific API (for Indian holiday detection)

JSON storage (orders, user data)

Ideal Use Case:

Shopkeepers, traders, service providers, or anyone needing seamless digital tracking and management of multi-platform orders, payments, and delivery workflow.

How to Deploy:

Works locally or on cloud platforms like Render.

Easy setup: requirements in requirements.txt, one config file for credentials, ready for GitHub and CI/CD.

Customization:

Extendable to more platforms, user roles, dashboards.

Holiday API logic can be adapted for any country or calendar.

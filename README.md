# Order Management System

A full-featured and modern Flask application for tracking, managing, and analyzing orders, payments, deliveries, and financials — designed for small businesses, shop owners, and individuals.

## Features

- **Order Tracking:** Add, edit, and view orders across multiple platforms.
- **Delivery Management:** Update and mark delivery statuses, with automatic date recording.
- **EMI Reminders:** Smart reminders for EMI payment orders, calculated using working days (excluding weekends and Indian public holidays via live Calendarific API).
- **Financial Dashboard:** Interactive analytics for monthly/yearly spend, profit/loss, and owner/category breakdowns.
- **File Management:** Upload order-related documents (screenshots, PDFs) with optional Google Drive backup via rclone.
- **Secure Login:** Session-based authentication for safe access.
- **Mobile-Friendly:** Responsive design for desktop and mobile views.

## Technology Stack

- Python (Flask)
- HTML, CSS, JavaScript (Bootstrap, Chart.js, DataTables)
- Google Drive (via rclone)
- Calendarific API for holiday detection
- JSON file storage

## Installation

1. **Clone the Repository:**
    ```
    git clone https://github.com/your-username/order-management-system.git
    cd order-management-system
    ```
2. **Install Dependencies:**
    ```
    pip install -r requirements.txt
    ```
3. **Set Calendarific API Key:**
    Register at https://calendarific.com for a free API key.  
    Set as environment variable:
    ```
    export CALENDARIFIC_API_KEY=your_actual_key
    ```
    Or update directly in `app.py`.

4. **Run the App Locally:**
    ```
    python app.py
    ```

## License

This project is open-source and free for personal and business use.

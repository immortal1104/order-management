"""
app.py

Smart Order Tracker - Flask Application

Version: 4.3

Highlights in v4.3:
- EMI reminders use Indian public holidays from Calendarific API and exclude weekends.
- If today is a holiday, reminders are deferred by +1 working day.
- All previous app features and routes retained; see "INDEX" for updated holiday logic.
"""

import os
import re
import json
from collections import defaultdict
from datetime import datetime, date, timedelta
import requests

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# ---------------- APP CONFIG ----------------

app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

UPLOAD_FOLDER = 'uploads'
ORDERS_FILE = 'orders.json'
CARDS_FILE = 'cards.json'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

orders = []

USER_CREDENTIALS = {
    "7206491113.os@gmail.com": "bittu@123"
}

# ------------------- GOOGLE DRIVE SETUP -------------------

gauth = GoogleAuth()
gauth.LoadCredentialsFile("mycreds.txt")
if not gauth.credentials or gauth.access_token_expired:
    if gauth.credentials and getattr(gauth.credentials, 'refresh_token', None):
        gauth.Refresh()
    else:
        gauth.LocalWebserverAuth()
    gauth.SaveCredentialsFile("mycreds.txt")
else:
    gauth.Authorize()

drive = GoogleDrive(gauth)

# Helper to get or create folder on Drive
def get_or_create_folder(folder_name, parent_id=None):
    query = f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    folder_list = drive.ListFile({'q': query}).GetList()
    if folder_list:
        return folder_list[0]['id']
    metadata = {'title': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
    if parent_id:
        metadata['parents'] = [{'id': parent_id}]
    folder = drive.CreateFile(metadata)
    folder.Upload()
    return folder['id']

# Helper to find file by name in folder on Drive
def get_file_in_folder(folder_id, filename):
    query = f"title='{filename}' and '{folder_id}' in parents and trashed=false"
    file_list = drive.ListFile({'q': query}).GetList()
    if file_list:
        return file_list[0]
    return None

def upload_file_pydrive(local_path, fy, folder):
    root_folder_id = get_or_create_folder("OrderUploads")
    fy_folder_id = get_or_create_folder(fy, parent_id=root_folder_id)
    target_folder_id = get_or_create_folder(folder, parent_id=fy_folder_id)
    file_drive = drive.CreateFile({'title': os.path.basename(local_path),
                                  'parents': [{'id': target_folder_id}]})
    file_drive.SetContentFile(local_path)
    file_drive.Upload()
    file_drive.InsertPermission({'type': 'anyone', 'value': 'anyone', 'role': 'reader'})
    return f"https://drive.google.com/open?id={file_drive['id']}"

# ------------------- UTILS -------------------

def safe_slug(text):
    text = text.lower().strip() if text else ''
    for tld in ['.com', '.net', '.org', '.in']:
        text = text.replace(tld, '')
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def normalize_number(value):
    try:
        f = float(value)
        if f.is_integer():
            return int(f)
        return round(f, 2)
    except:
        return 0

# Updated load_orders to load from Google Drive
def load_orders():
    global orders
    try:
        folder_id = get_or_create_folder("OrderData")
        print(f"[DEBUG] Using folder ID: {folder_id}")

        query = f"'{folder_id}' in parents and title = '{ORDERS_FILE}' and trashed = false"
        files = drive.ListFile({'q': query}).GetList()

        if not files:
            print(f"[DEBUG] No file named {ORDERS_FILE} found in folder")
            orders = []
            return

        file = files[0]
        print(f"[DEBUG] Found file '{file['title']}' with ID {file['id']}")

        content_str = file.GetContentString()
        orders = json.loads(content_str)
        print(f"[DEBUG] Loaded {len(orders)} orders from Drive")

    except Exception as e:
        print(f"[ERROR] Failed to load orders from Drive: {e}")
        orders = []

# Updated save_orders to save to Google Drive
def save_orders():
    global orders
    folder_id = get_or_create_folder("OrderData")
    file_obj = get_file_in_folder(folder_id, ORDERS_FILE)
    content = json.dumps(orders, indent=2)
    try:
        if file_obj:
            file_obj.SetContentString(content)
        else:
            file_obj = drive.CreateFile({'title': ORDERS_FILE, 'parents': [{'id': folder_id}]})
            file_obj.SetContentString(content)
        file_obj.Upload()
    except Exception as e:
        print(f"Error saving orders to Google Drive: {e}")

def load_cards():
    try:
        with open(CARDS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def calculate_profit_loss(purchase, sell):
    try:
        return round(float(sell) - float(purchase), 2)
    except:
        return 0.0

def get_financial_year(date_str):
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
    except:
        dt = datetime.today()
    return f"{dt.year}-{dt.year+1}" if dt.month >= 4 else f"{dt.year-1}-{dt.year}"

@app.template_filter()
def datetimeformat(value, fmt='%d %b %Y'):
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime(fmt)
    except:
        return value

@app.template_filter()
def month_label(value):
    try:
        dt = datetime.strptime(value, '%Y-%m')
        return dt.strftime('%B %Y')
    except:
        return value

def generate_drive_open_link(file_id):
    return f"https://drive.google.com/open?id={file_id}"

# ------------- EMI/Working Day/Holiday LOGIC -------------

def fetch_calendarific_holidays(year=None):
    if year is None:
        year = date.today().year
    api_key = "9sI48BBdHs2tT9IsXdgs4dSqBLXeUFCp"  # Insert your Calendarific API key here
    url = f"https://calendarific.com/api/v2/holidays?api_key={api_key}&country=IN&year={year}"
    try:
        resp = requests.get(url)
        if resp.ok:
            data = resp.json()
            holidays = data['response']['holidays']
            return set([h['date']['iso'] for h in holidays if h.get('type', [''])[0].lower() == 'national'])
        else:
            print("Calendarific API error:", resp.text)
    except Exception as e:
        print("Calendarific error:", e)
    return {f"{year}-01-26", f"{year}-08-15", f"{year}-10-02"}

def count_working_days(start, end, holidays_set):
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5 and current.strftime('%Y-%m-%d') in holidays_set:
            current += timedelta(days=1)
            continue
        if current.weekday() < 5 and current.strftime('%Y-%m-%d') not in holidays_set:
            count += 1
        current += timedelta(days=1)
    return count

# ------------------- FILE HANDLER -------------------

def save_files(files, fy, date_obj, order_no, platform, pay_mode, folder):
    saved = []
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], fy, folder)
    os.makedirs(folder_path, exist_ok=True)
    date_str = date_obj.strftime('%d-%b-%Y').lower()
    components = [safe_slug(date_str), safe_slug(order_no), safe_slug(platform), safe_slug(pay_mode)]
    filestamp = '-'.join(filter(None, components))
    for file in files:
        if not file or not file.filename:
            continue
        ext = os.path.splitext(file.filename)[1].lower()
        allowed_ext = {'jpg', 'jpeg', 'png', 'gif'} if folder == 'screenshots' else {'pdf'}
        if ext[1:] not in allowed_ext:
            continue
        filename = secure_filename(f"{filestamp}{ext}")
        local_path = os.path.join(folder_path, filename)
        file.save(local_path)
        try:
            public_link = upload_file_pydrive(local_path, fy, folder)
            saved.append({'link': public_link, 'path': f'drive:{filename}'})
            os.remove(local_path)
        except Exception as e:
            flash(f"Upload failed for {filename}: {str(e)}", "danger")
            continue
    return saved

# ------------------- AUTH -------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        if USER_CREDENTIALS.get(email) == password:
            session.permanent = True
            session['user'] = email
            flash("✅ Login successful", "success")
            return redirect(url_for('index'))
        flash("❌ Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("🔒 Logged out", "info")
    return redirect(url_for('login'))

# ------------------- AJAX CHECK -------------------

@app.route('/check_order_exists', methods=['POST'])
def check_order_exists():
    if 'user' not in session:
        return jsonify({'exists': False}), 401
    load_orders()
    order_no = request.json.get('order_number', '').strip()
    return jsonify({'exists': any(o['order_number'] == order_no for o in orders)})

# ------------------- INDEX -------------------

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    load_orders()
    today = date.today()
    holidays_set = fetch_calendarific_holidays(today.year)
    is_today_holiday = today.strftime('%Y-%m-%d') in holidays_set
    reminder_ref_date = today + timedelta(days=1) if is_today_holiday else today

    for o in orders:
        try:
            order_dt = datetime.strptime(o.get('order_date', ''), '%Y-%m-%d').date()
        except Exception:
            continue
        payment_mode = str(o.get('payment_mode', '')).lower()
        working_days_since = count_working_days(order_dt, reminder_ref_date, holidays_set)

        if 3 <= working_days_since <= 5 and "emi" in payment_mode and not is_today_holiday:
            emi_msg = (f"📢 EMI Reminder — "
                       f"Order: {o.get('order_number')}, "
                       f"Purchase: ₹{o.get('purchase'):,.2f}, "
                       f"Payment Mode: {o.get('payment_mode')}")
            flash(emi_msg, 'emi')

    return render_template('index.html', orders=orders, date=today)

@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200

# ------------------- UPDATE DELIVERY STATUS -------------------

@app.route('/update_delivery_status', methods=['POST'])
def update_delivery_status():
    if 'user' not in session:
        return jsonify(success=False), 401
    load_orders()
    data = request.get_json()
    order_no = data.get('order_number')
    status = int(data.get('delivery_status', 0))
    for o in orders:
        if o['order_number'] == order_no:
            o['delivery_status'] = status
            if status == 1 and float(o.get('sell', 0) or 0) == 0:
                o['order_delivered'] = datetime.today().strftime('%Y-%m-%d')
            save_orders()
            return jsonify(success=True)
    return jsonify(success=False)

# ------------------- DASHBOARD -------------------

@app.route('/pl_metrics_dashboard', methods=['GET'])
def pl_metrics_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    load_orders()
    cards_map = load_cards()
    owners_full = list(cards_map.keys())
    owners_plot = owners_full + ['Others']

    months = sorted({o.get('order_date', '')[:7] for o in orders if o.get('order_date')})
    current_month = datetime.now().strftime('%Y-%m')
    selected_month = request.args.get('month', current_month)
    if selected_month not in months and months:
        selected_month = months[-1]

    earning = sum(o.get('profit_loss', 0) for o in orders if o.get('profit_loss', 0) > 0 and o.get('order_date', '').startswith(selected_month))
    total_spent = sum(o.get('spent', 0) for o in orders if o.get('order_date', '').startswith(selected_month))
    total_received = sum(o.get('cash_received', 0) for o in orders if o.get('order_date', '').startswith(selected_month))
    cash_pending = sum(float(o.get('sell', 0) or 0) for o in orders if float(o.get('cash_received', 0) or 0) == 0)

    stock_orders = [o for o in orders if int(o.get('delivery_status', 0)) == 1 and float(o.get('sell', 0) or 0) == 0]
    total_stock_available = len(stock_orders)
    stock_table = stock_orders

    yet_to_deliver_orders = [o for o in orders if float(o.get('sell', 0) or 0) == 0 and int(o.get('delivery_status', 0)) == 0]

    monthly_spend = defaultdict(float)
    for o in orders:
        if o.get('order_date', '')[:7] != selected_month:
            continue
        spent = float(o.get('spent', 0) or 0)
        pmode = o.get('payment_mode', '')
        m = re.search(r'\b(\d{4})\b', pmode)
        card_num = m.group(1) if m else ''
        owner = next((k for k, v in cards_map.items() if card_num in v), 'Others')
        monthly_spend[owner] += spent
    monthly_data = {k: monthly_spend.get(k, 0) for k in owners_plot}

    yearly_spend = {}
    for o in orders:
        spent = float(o.get('spent', 0) or 0)
        pmode = o.get('payment_mode', '')
        m = re.search(r'\b(\d{4})\b', pmode)
        card_num = m.group(1) if m else ''
        owner = next((k for k, v in cards_map.items() if card_num in v), 'Others')
        fy = get_financial_year(o.get('order_date', ''))
        yearly_spend.setdefault(fy, defaultdict(float))
        yearly_spend[fy][owner] += spent
    years = sorted(yearly_spend.keys())
    latest_year = years[-1] if years else ''
    yearly_map = yearly_spend.get(latest_year, defaultdict(float))
    yearly_data = {k: yearly_map.get(k, 0) for k in owners_plot}

    cash_pending_orders = [
        {
            'order_number': o.get('order_number', ''),
            'model_number': o.get('model_number', ''),
            'to_supply': o.get('to_supply', ''),
            'cash_pending': float(o.get('sell', 0) or 0)
        }
        for o in orders if float(o.get('cash_received', 0) or 0) == 0 and float(o.get('sell', 0) or 0) > 0
    ]

    return render_template('pl_metrics_dashboard.html',
                           dashboard={
                               'Earning': earning,
                               'Total Stock Available': total_stock_available,
                               'Cash Pending': cash_pending,
                               'Total Spent': total_spent,
                               'Total Received': total_received,
                               'Yet to Deliver': len(yet_to_deliver_orders),
                           },
                           months=months,
                           selected_month=selected_month,
                           monthly_data=monthly_data,
                           yearly_data=yearly_data,
                           latest_year=latest_year,
                           stock_table=stock_table,
                           cash_pending_orders=cash_pending_orders,
                           yet_to_deliver_orders=yet_to_deliver_orders)

# ------------------- ADD ORDER -------------------

@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session:
        return redirect(url_for('login'))
    global orders
    load_orders()

    form = request.form
    order_no = form.get('order_number', '').strip()
    if any(o['order_number'] == order_no for o in orders):
        flash(f"Order {order_no} already exists", "danger")
        return redirect(url_for('index'))

    try:
        date_obj = datetime.strptime(form.get('order_date'), '%Y-%m-%d')
    except:
        date_obj = datetime.today()

    fy = get_financial_year(form.get('order_date') or date_obj.strftime('%Y-%m-%d'))
    screenshots = save_files(request.files.getlist('screenshots'), fy, date_obj, order_no,
                             form.get('platform'), form.get('payment_mode'), 'screenshots')
    pdfs = save_files(request.files.getlist('pdfs'), fy, date_obj, order_no,
                      form.get('platform'), form.get('payment_mode'), 'pdfs')
    orders.append({
        'platform': form.get('platform'),
        'order_number': order_no,
        'model_number': form.get('model_number'),
        'purchase': normalize_number(form.get('purchase', 0)),
        'sell': normalize_number(form.get('sell', 0)),
        'profit_loss': calculate_profit_loss(form.get('purchase'), form.get('sell')),
        'payment_mode': form.get('payment_mode'),
        'spent': normalize_number(form.get('spent', 0)),
        'order_date': form.get('order_date'),
        'order_delivered': form.get('order_delivered'),
        'mobile_number': form.get('mobile_number'),
        'to_supply': form.get('to_supply'),
        'cash_received': normalize_number(form.get('cash_received', 0)),
        'memo': form.get('memo'),
        'screenshots': screenshots,
        'pdfs': pdfs,
        'delivery_status': int(form.get('delivery_status', 0))
    })

    save_orders()
    flash("✅ Order added successfully", "success")
    return redirect(url_for('index'))

# ------------------- EDIT ORDER -------------------

@app.route('/edit/<order_number>', methods=['POST'])
def edit(order_number):
    if 'user' not in session:
        return redirect(url_for('login'))
    global orders
    load_orders()

    order = next((o for o in orders if o['order_number'] == order_number), None)
    if not order:
        flash("Order not found", "danger")
        return redirect(url_for('index'))

    form = request.form
    updated_number = form.get('order_number', '').strip()
    if updated_number != order_number and any(o['order_number'] == updated_number for o in orders):
        flash("Duplicate order number", "danger")
        return redirect(url_for('index'))

    try:
        date_obj = datetime.strptime(form.get('order_date'), '%Y-%m-%d')
    except:
        date_obj = datetime.today()

    fy = get_financial_year(form.get('order_date') or date_obj.strftime('%Y-%m-%d'))
    screenshots = save_files(request.files.getlist('screenshots'), fy, date_obj, updated_number,
                             form.get('platform'), form.get('payment_mode'), 'screenshots')
    pdfs = save_files(request.files.getlist('pdfs'), fy, date_obj, updated_number,
                      form.get('platform'), form.get('payment_mode'), 'pdfs')

    order.update({
        'platform': form.get('platform'),
        'order_number': updated_number,
        'model_number': form.get('model_number'),
        'purchase': normalize_number(form.get('purchase', 0)),
        'sell': normalize_number(form.get('sell', 0)),
        'profit_loss': calculate_profit_loss(form.get('purchase'), form.get('sell')),
        'payment_mode': form.get('payment_mode'),
        'spent': normalize_number(form.get('spent', 0)),
        'order_date': form.get('order_date'),
        'order_delivered': form.get('order_delivered'),
        'mobile_number': form.get('mobile_number'),
        'to_supply': form.get('to_supply'),
        'cash_received': normalize_number(form.get('cash_received', 0)),
        'memo': form.get('memo'),
        'screenshots': order.get('screenshots', []) + screenshots,
        'pdfs': order.get('pdfs', []) + pdfs,
        'delivery_status': int(form.get('delivery_status', order.get('delivery_status', 0)))
    })

    save_orders()
    flash("✅ Order updated successfully", "success")
    return redirect(url_for('index'))

# ------------------- DELETE FILE -------------------

@app.route('/delete-file/<order_number>', methods=['POST'])
def delete_file(order_number):
    if 'user' not in session:
        return redirect(url_for('login'))
    filepath = request.form.get('filepath')
    load_orders()

    for o in orders:
        if o['order_number'] == order_number:
            for key in ['screenshots', 'pdfs']:
                new_files = []
                for f in o.get(key, []):
                    path = f.get('path') if isinstance(f, dict) else None
                    link = f.get('link') if isinstance(f, dict) else None
                    if f == filepath or path == filepath:
                        if link:
                            file_id_match = re.search(r'id=([a-zA-Z0-9_-]+)', link)
                            if file_id_match:
                                file_id = file_id_match.group(1)
                                try:
                                    file_drive = drive.CreateFile({'id': file_id})
                                    file_drive.Delete()
                                    flash("✅ File deleted from Google Drive", "success")
                                except Exception as e:
                                    flash(f"⚠️ Failed to delete from Drive: {str(e)}", "warning")
                                    continue
                    else:
                        new_files.append(f)
                o[key] = new_files
            break

    save_orders()
    return redirect(url_for('index'))

# ------------------- DELETE ORDER -------------------

@app.route('/delete/<order_number>', methods=['POST'])
def delete_order(order_number):
    if 'user' not in session:
        return redirect(url_for('login'))

    global orders
    load_orders()

    order_to_delete = next((o for o in orders if o['order_number'] == order_number), None)

    if order_to_delete:
        linked_files = []
        for key in ['screenshots', 'pdfs']:
            linked_files.extend(order_to_delete.get(key, []))
        for file_obj in linked_files:
            if isinstance(file_obj, dict) and 'link' in file_obj:
                link = file_obj['link']
                match = re.search(r'id=([a-zA-Z0-9_-]+)', link)
                if match:
                    file_id = match.group(1)
                    try:
                        file_drive = drive.CreateFile({'id': file_id})
                        file_drive.Delete()
                    except Exception as e:
                        print(f"Error deleting file {file_id} from Drive: {e}")

        orders = [o for o in orders if o['order_number'] != order_number]
        save_orders()
        flash(f"🗑 Order {order_number} and its files deleted successfully", "success")
    else:
        flash(f"Order {order_number} not found", "danger")

    return redirect(url_for('index'))

# ------------------- CASH RECEIVED -------------------

@app.route('/mark_cash_received', methods=['POST'])
def mark_cash_received():
    if 'user' not in session:
        return jsonify(success=False), 401

    load_orders()
    data = request.get_json()
    order_no = data.get('order_number')

    for o in orders:
        if o['order_number'] == order_no:
            if float(o.get('cash_received', 0)) < float(o.get('sell', 0)):
                o['cash_received'] = float(o.get('sell', 0))
            save_orders()
            return jsonify(success=True)

    return jsonify(success=False)

# ------------------- MARK DELIVERED -------------------

@app.route('/mark_delivered', methods=['POST'])
def mark_delivered():
    if 'user' not in session:
        return jsonify(success=False), 401

    load_orders()
    order_no = request.form.get('order_number')
    action = request.form.get('action')

    for o in orders:
        if o['order_number'] == order_no:
            if action == 'Delivered':
                o['sell'] = 0
                o['delivery_status'] = 1
                o['order_delivered'] = datetime.today().strftime('%Y-%m-%d')
            elif action == 'Cancelled':
                o['delivery_status'] = 'cancel'
            elif action == 'Not Delivered':
                o['delivery_status'] = 0
            save_orders()
            return jsonify(success=True)

    return jsonify(success=False)

# ------------------- MAIN -------------------

if __name__ == '__main__':
    app.run(debug=True)

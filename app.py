import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='templates')

SUPABASE_CONFIG = {
    "host": os.environ.get("SUPABASE_HOST", "db.oemmhemsmhtlkdasvdjy.supabase.co"),
    "port": int(os.environ.get("SUPABASE_PORT", 5432)),
    "dbname": os.environ.get("SUPABASE_DB", "postgres"),
    "user": os.environ.get("SUPABASE_USER", "postgres"),
    "password": os.environ.get("SUPABASE_PASS", "#Paresh@7359")
}

def get_db():
    return psycopg2.connect(
        host=SUPABASE_CONFIG["host"],
        port=SUPABASE_CONFIG["port"],
        dbname=SUPABASE_CONFIG["dbname"],
        user=SUPABASE_CONFIG["user"],
        password=SUPABASE_CONFIG["password"],
        connect_timeout=10,
        cursor_factory=RealDictCursor
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

# ----------------- DASHBOARD API -----------------
@app.route('/api/dashboard')
def api_dashboard():
    period = request.args.get('period', 'today')
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    
    if period == 'yesterday':
        from_d = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        to_d = from_d
    elif period == 'week':
        from_d = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
        to_d = today_str
    elif period == 'month':
        from_d = now.strftime('%Y-%m-01')
        to_d = today_str
    elif period == 'year':
        from_d = now.strftime('%Y-01-01')
        to_d = today_str
    elif period == 'all':
        from_d, to_d = None, None
    else: # today
        from_d = today_str
        to_d = today_str

    conn = get_db()
    cur = conn.cursor()

    if from_d and to_d:
        cur.execute("SELECT COALESCE(SUM(grand_total), 0) AS total, COALESCE(SUM(gst_amount), 0) AS gst, COALESCE(SUM(udhar), 0) AS udhar, COUNT(*) AS count FROM sales WHERE created_at >= %s AND created_at <= %s", (f"{from_d} 00:00:00", f"{to_d} 23:59:59"))
        sales_stat = cur.fetchone()
        
        cur.execute("SELECT COALESCE(SUM(final_amount), 0) AS total, COUNT(*) AS count FROM repairs WHERE received_date >= %s AND received_date <= %s", (from_d, to_d))
        repairs_stat = cur.fetchone()

        cur.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE created_at >= %s AND created_at <= %s", (f"{from_d} 00:00:00", f"{to_d} 23:59:59"))
        expenses_stat = cur.fetchone()
    else:
        cur.execute("SELECT COALESCE(SUM(grand_total), 0) AS total, COALESCE(SUM(gst_amount), 0) AS gst, COALESCE(SUM(udhar), 0) AS udhar, COUNT(*) AS count FROM sales")
        sales_stat = cur.fetchone()

        cur.execute("SELECT COALESCE(SUM(final_amount), 0) AS total, COUNT(*) AS count FROM repairs")
        repairs_stat = cur.fetchone()

        cur.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM expenses")
        expenses_stat = cur.fetchone()

    cur.execute("SELECT COALESCE(SUM(stock), 0) AS total_stock, COUNT(*) AS total_models FROM products")
    stock_stat = cur.fetchone()

    cur.execute("SELECT COUNT(*) AS count FROM customers")
    cust_count = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) AS pending FROM repairs WHERE status NOT IN ('Delivered', 'Cancelled')")
    pending_repairs = cur.fetchone()['pending']

    # Recent Sales
    cur.execute("SELECT id, invoice_no, customer_name, grand_total, created_at, sale_type FROM sales ORDER BY id DESC LIMIT 6")
    recent_sales = cur.fetchall()

    # Recent Repairs
    cur.execute("SELECT id, repair_no, customer, phone_model, problem, final_amount, status, received_date FROM repairs ORDER BY id DESC LIMIT 6")
    recent_repairs = cur.fetchall()

    conn.close()

    return jsonify({
        "sales_total": float(sales_stat['total']),
        "sales_count": int(sales_stat['count']),
        "gst_total": float(sales_stat['gst']),
        "udhar_total": float(sales_stat['udhar']),
        "repairs_total": float(repairs_stat['total']),
        "repairs_count": int(repairs_stat['count']),
        "expenses_total": float(expenses_stat['total']),
        "total_stock": int(stock_stat['total_stock']),
        "total_models": int(stock_stat['total_models']),
        "customer_count": cust_count,
        "pending_repairs": pending_repairs,
        "recent_sales": recent_sales,
        "recent_repairs": recent_repairs
    })

# ----------------- PRODUCTS API -----------------
@app.route('/api/products', methods=['GET', 'POST'])
def api_products():
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'GET':
        q = request.args.get('q', '').strip()
        if q:
            cur.execute("""SELECT * FROM products WHERE brand ILIKE %s OR model ILIKE %s OR imei1 ILIKE %s OR imei2 ILIKE %s OR serial_no ILIKE %s ORDER BY id DESC""",
                        (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"))
        else:
            cur.execute("SELECT * FROM products ORDER BY id DESC")
        items = cur.fetchall()
        conn.close()
        return jsonify(items)
    
    data = request.json
    try:
        cur.execute("""INSERT INTO products(brand, model, imei1, imei2, serial_no, ram, storage, color, purchase_price, sale_price, gst, stock, supplier, created_at)
                       VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (data.get('brand'), data.get('model'), data.get('imei1'), data.get('imei2'), data.get('serial_no'),
                     data.get('ram'), data.get('storage'), data.get('color'), float(data.get('purchase_price') or 0),
                     float(data.get('sale_price') or 0), float(data.get('gst') or 0), int(data.get('stock') or 1),
                     data.get('supplier'), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        new_id = cur.fetchone()['id']
        conn.commit()
        conn.close()
        return jsonify({"success": True, "id": new_id})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 400

@app.route('/api/products/<int:pid>', methods=['PUT', 'DELETE'])
def api_product_detail(pid):
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'DELETE':
        cur.execute("DELETE FROM products WHERE id=%s", (pid,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    
    data = request.json
    try:
        cur.execute("""UPDATE products SET brand=%s, model=%s, imei1=%s, imei2=%s, serial_no=%s, ram=%s, storage=%s, color=%s,
                       purchase_price=%s, sale_price=%s, gst=%s, stock=%s, supplier=%s WHERE id=%s""",
                    (data.get('brand'), data.get('model'), data.get('imei1'), data.get('imei2'), data.get('serial_no'),
                     data.get('ram'), data.get('storage'), data.get('color'), float(data.get('purchase_price') or 0),
                     float(data.get('sale_price') or 0), float(data.get('gst') or 0), int(data.get('stock') or 0),
                     data.get('supplier'), pid))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 400

# ----------------- CUSTOMERS API -----------------
@app.route('/api/customers', methods=['GET', 'POST'])
def api_customers():
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'GET':
        q = request.args.get('q', '').strip()
        if q:
            cur.execute("SELECT * FROM customers WHERE name ILIKE %s OR mobile ILIKE %s ORDER BY name ASC", (f"%{q}%", f"%{q}%"))
        else:
            cur.execute("SELECT * FROM customers ORDER BY opening_balance DESC, name ASC")
        items = cur.fetchall()
        conn.close()
        return jsonify(items)

    data = request.json
    try:
        cur.execute("""INSERT INTO customers(name, mobile, address, gstin, opening_balance, notes, created_at)
                       VALUES(%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (data.get('name'), data.get('mobile'), data.get('address'), data.get('gstin'),
                     float(data.get('opening_balance') or 0), data.get('notes'), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        new_id = cur.fetchone()['id']
        conn.commit()
        conn.close()
        return jsonify({"success": True, "id": new_id})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 400

@app.route('/api/customers/<int:cid>', methods=['PUT', 'DELETE'])
def api_customer_detail(cid):
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'DELETE':
        cur.execute("DELETE FROM customers WHERE id=%s", (cid,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    data = request.json
    try:
        cur.execute("""UPDATE customers SET name=%s, mobile=%s, address=%s, gstin=%s, opening_balance=%s, notes=%s WHERE id=%s""",
                    (data.get('name'), data.get('mobile'), data.get('address'), data.get('gstin'),
                     float(data.get('opening_balance') or 0), data.get('notes'), cid))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 400

# ----------------- SALES & INVOICE API -----------------
@app.route('/api/sales', methods=['GET', 'POST'])
def api_sales():
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'GET':
        q = request.args.get('q', '').strip()
        if q:
            cur.execute("SELECT * FROM sales WHERE invoice_no ILIKE %s OR customer_name ILIKE %s ORDER BY id DESC", (f"%{q}%", f"%{q}%"))
        else:
            cur.execute("SELECT * FROM sales ORDER BY id DESC LIMIT 100")
        items = cur.fetchall()
        conn.close()
        return jsonify(items)

    data = request.json
    items = data.get('items', [])
    if not items:
        conn.close()
        return jsonify({"error": "Cart is empty"}), 400

    # Auto generate Invoice Number for current year
    year = datetime.now().year
    prefix = f"INV-{year}-"
    cur.execute("SELECT invoice_no FROM sales WHERE invoice_no LIKE %s ORDER BY id DESC LIMIT 1", (f"{prefix}%",))
    last_inv = cur.fetchone()
    if last_inv and last_inv['invoice_no']:
        try:
            num = int(last_inv['invoice_no'].split('-')[-1]) + 1
        except Exception:
            num = 1
    else:
        num = 1
    invoice_no = f"INV-{year}-{num:05d}"

    cust_name = data.get('customer_name')
    cust_id = data.get('customer_id')
    sale_type = data.get('sale_type', 'GST')
    subtotal = float(data.get('subtotal') or 0)
    gst_amt = float(data.get('gst_amount') or 0)
    grand_total = float(data.get('grand_total') or 0)
    cash = float(data.get('cash') or 0)
    upi = float(data.get('upi') or 0)
    bank = float(data.get('bank') or 0)
    card = float(data.get('card') or 0)
    udhar = float(data.get('udhar') or 0)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cur.execute("""INSERT INTO sales(invoice_no, customer_id, customer_name, sale_type, subtotal, gst_amount, grand_total, cash, upi, bank, card, udhar, created_at)
                       VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (invoice_no, cust_id, cust_name, sale_type, subtotal, gst_amt, grand_total, cash, upi, bank, card, udhar, created_at))
        sale_id = cur.fetchone()['id']

        for it in items:
            cur.execute("""INSERT INTO sale_items(sale_id, product_id, product_name, imei, qty, rate, gst, taxable, gst_amount, amount)
                           VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (sale_id, it.get('pid'), it.get('name'), it.get('imei'), it.get('qty', 1), it.get('rate', 0), it.get('gst', 0),
                         it.get('taxable', 0), it.get('gstamt', 0), it.get('amount', 0)))
            if it.get('pid'):
                cur.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (it.get('qty', 1), it.get('pid')))

        if cust_id and udhar > 0:
            cur.execute("UPDATE customers SET opening_balance = opening_balance + %s WHERE id = %s", (udhar, cust_id))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "invoice_no": invoice_no, "id": sale_id})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 400

@app.route('/api/sales/<int:sid>', methods=['DELETE'])
def api_cancel_sale(sid):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT product_id, qty FROM sale_items WHERE sale_id=%s", (sid,))
        for it in cur.fetchall():
            if it['product_id']:
                cur.execute("UPDATE products SET stock = stock + %s WHERE id=%s", (it['qty'], it['product_id']))
        cur.execute("DELETE FROM sale_items WHERE sale_id=%s", (sid,))
        cur.execute("DELETE FROM sales WHERE id=%s", (sid,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 400

# ----------------- REPAIRS API -----------------
@app.route('/api/repairs', methods=['GET', 'POST'])
def api_repairs():
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'GET':
        q = request.args.get('q', '').strip()
        if q:
            cur.execute("SELECT * FROM repairs WHERE repair_no ILIKE %s OR customer ILIKE %s OR phone_model ILIKE %s OR mobile ILIKE %s ORDER BY id DESC",
                        (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"))
        else:
            cur.execute("SELECT * FROM repairs ORDER BY id DESC")
        items = cur.fetchall()
        conn.close()
        return jsonify(items)

    data = request.json
    year = datetime.now().year
    prefix = f"REP-{year}-"
    cur.execute("SELECT repair_no FROM repairs WHERE repair_no LIKE %s ORDER BY id DESC LIMIT 1", (f"{prefix}%",))
    last_r = cur.fetchone()
    if last_r and last_r['repair_no']:
        try:
            num = int(last_r['repair_no'].split('-')[-1]) + 1
        except Exception:
            num = 1
    else:
        num = 1
    repair_no = f"REP-{year}-{num:05d}"

    final_amt = float(data.get('final_amount') or 0)
    advance = float(data.get('advance') or 0)
    pending = max(0, final_amt - advance)

    try:
        cur.execute("""INSERT INTO repairs(repair_no, customer, mobile, phone_model, imei, problem, estimate, final_amount, advance, pending, status, technician, received_date, expected_date, notes)
                       VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (repair_no, data.get('customer'), data.get('mobile'), data.get('phone_model'), data.get('imei'),
                     data.get('problem'), float(data.get('estimate') or 0), final_amt, advance, pending,
                     data.get('status', 'Received'), data.get('technician'), datetime.now().strftime("%Y-%m-%d"),
                     data.get('expected_date'), data.get('notes')))
        new_id = cur.fetchone()['id']
        conn.commit()
        conn.close()
        return jsonify({"success": True, "repair_no": repair_no, "id": new_id})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 400

@app.route('/api/repairs/<int:rid>', methods=['PUT', 'DELETE'])
def api_repair_detail(rid):
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'DELETE':
        cur.execute("DELETE FROM repairs WHERE id=%s", (rid,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    data = request.json
    final_amt = float(data.get('final_amount') or 0)
    advance = float(data.get('advance') or 0)
    pending = max(0, final_amt - advance)
    try:
        cur.execute("""UPDATE repairs SET customer=%s, mobile=%s, phone_model=%s, imei=%s, problem=%s, estimate=%s,
                       final_amount=%s, advance=%s, pending=%s, status=%s, technician=%s, expected_date=%s, notes=%s WHERE id=%s""",
                    (data.get('customer'), data.get('mobile'), data.get('phone_model'), data.get('imei'),
                     data.get('problem'), float(data.get('estimate') or 0), final_amt, advance, pending,
                     data.get('status'), data.get('technician'), data.get('expected_date'), data.get('notes'), rid))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 400

# ----------------- EXPENSES API -----------------
@app.route('/api/expenses', methods=['GET', 'POST'])
def api_expenses():
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'GET':
        cur.execute("SELECT * FROM expenses ORDER BY id DESC LIMIT 100")
        items = cur.fetchall()
        conn.close()
        return jsonify(items)

    data = request.json
    try:
        cur.execute("""INSERT INTO expenses(category, description, amount, payment_mode, created_at)
                       VALUES(%s, %s, %s, %s, %s) RETURNING id""",
                    (data.get('category'), data.get('description'), float(data.get('amount') or 0),
                     data.get('payment_mode', 'Cash'), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        new_id = cur.fetchone()['id']
        conn.commit()
        conn.close()
        return jsonify({"success": True, "id": new_id})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 400

@app.route('/api/expenses/<int:eid>', methods=['DELETE'])
def api_delete_expense(eid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id=%s", (eid,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ----------------- SETTINGS API -----------------
@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'GET':
        cur.execute("SELECT * FROM settings WHERE id=1")
        item = cur.fetchone()
        conn.close()
        return jsonify(item or {})

    data = request.json
    try:
        cur.execute("""UPDATE settings SET shop_name=%s, owner_name=%s, mobile=%s, email=%s, address=%s, gstin=%s,
                       bank_name=%s, bank_account=%s, bank_ifsc=%s, bank_holder=%s, upi_id=%s, invoice_terms=%s, invoice_footer=%s WHERE id=1""",
                    (data.get('shop_name'), data.get('owner_name'), data.get('mobile'), data.get('email'),
                     data.get('address'), data.get('gstin'), data.get('bank_name'), data.get('bank_account'),
                     data.get('bank_ifsc'), data.get('bank_holder'), data.get('upi_id'),
                     data.get('invoice_terms'), data.get('invoice_footer')))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 400

# ----------------- VIEW / PRINT INVOICE -----------------
@app.route('/invoice/<invoice_no>')
def view_invoice(invoice_no):
    copy_type = request.args.get('copy', 'ORIGINAL').upper()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM settings WHERE id=1")
    settings = cur.fetchone() or {}

    cur.execute("SELECT * FROM sales WHERE invoice_no=%s", (invoice_no,))
    sale = cur.fetchone()
    if not sale:
        conn.close()
        return "Invoice not found", 404

    cur.execute("SELECT * FROM sale_items WHERE sale_id=%s", (sale['id'],))
    items = cur.fetchall()
    conn.close()

    return render_template('invoice.html', settings=settings, sale=sale, items=items, copy_type=copy_type)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATE_DIR)

# Supabase Configurations with IPv4 Pooler for Render / Cloud
SUPABASE_HOST = os.environ.get("SUPABASE_HOST", "aws-0-ap-south-1.pooler.supabase.com")
SUPABASE_PORT = int(os.environ.get("SUPABASE_PORT", 6543))
SUPABASE_DB = os.environ.get("SUPABASE_DB", "postgres")
SUPABASE_USER = os.environ.get("SUPABASE_USER", "postgres.oemmhemsmhtlkdasvdjy")
SUPABASE_PASS = os.environ.get("SUPABASE_PASS", "#Paresh@7359")

# Universal DB Connection (psycopg2 or pure-python pg8000 fallback)
USE_PSYCOPG2 = False
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    USE_PSYCOPG2 = True
except Exception:
    import pg8000.native

class DBWrapper:
    def __init__(self):
        # List of connection candidates (IPv4 Pooler -> Direct Host fallback)
        candidates = [
            {
                "host": SUPABASE_HOST,
                "port": SUPABASE_PORT,
                "database": SUPABASE_DB,
                "user": SUPABASE_USER,
                "password": SUPABASE_PASS,
            },
            {
                "host": "aws-0-ap-south-1.pooler.supabase.com",
                "port": 6543,
                "database": "postgres",
                "user": "postgres.oemmhemsmhtlkdasvdjy",
                "password": SUPABASE_PASS,
            },
            {
                "host": "db.oemmhemsmhtlkdasvdjy.supabase.co",
                "port": 5432,
                "database": "postgres",
                "user": "postgres",
                "password": SUPABASE_PASS,
            }
        ]

        self.conn = None
        self.driver = None

        for c in candidates:
            if USE_PSYCOPG2:
                try:
                    self.conn = psycopg2.connect(
                        host=c["host"],
                        port=c["port"],
                        dbname=c["database"],
                        user=c["user"],
                        password=c["password"],
                        connect_timeout=6,
                        cursor_factory=RealDictCursor
                    )
                    self.cur = self.conn.cursor()
                    self.driver = "psycopg2"
                    break
                except Exception:
                    pass

            if not self.conn:
                try:
                    import pg8000.native
                    self.conn = pg8000.native.Connection(
                        host=c["host"],
                        port=c["port"],
                        database=c["database"],
                        user=c["user"],
                        password=c["password"],
                        timeout=6
                    )
                    self.driver = "pg8000"
                    break
                except Exception:
                    pass

        if not self.conn:
            raise Exception("Could not connect to Supabase PostgreSQL database.")

    def execute(self, sql, params=None):
        if self.driver == "psycopg2":
            self.cur.execute(sql, params)
        else:
            self._pg8000_res = self.conn.run(sql, *(params if params else []))

    def fetchall(self):
        if self.driver == "psycopg2":
            rows = self.cur.fetchall()
            return [dict(r) for r in rows]
        else:
            if not hasattr(self, '_pg8000_res') or not self._pg8000_res:
                return []
            cols = [c['name'] for c in self.conn.columns]
            return [dict(zip(cols, row)) for row in self._pg8000_res]

    def fetchone(self):
        if self.driver == "psycopg2":
            r = self.cur.fetchone()
            return dict(r) if r else None
        else:
            if not hasattr(self, '_pg8000_res') or not self._pg8000_res:
                return None
            cols = [c['name'] for c in self.conn.columns]
            return dict(zip(cols, self._pg8000_res[0]))

    def commit(self):
        if self.driver == "psycopg2":
            self.conn.commit()

    def rollback(self):
        if self.driver == "psycopg2":
            self.conn.rollback()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

def get_db():
    return DBWrapper()

def load_template_text(name, fallback_text):
    paths = [
        os.path.join(BASE_DIR, 'templates', name),
        os.path.join(BASE_DIR, name),
        os.path.join(os.getcwd(), 'templates', name),
        os.path.join(os.getcwd(), name),
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                pass
    return fallback_text

EMBEDDED_INDEX_HTML = '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">\n    <title>Mobile Shop Manager - Cloud Web App</title>\n    <link rel="manifest" href="/manifest.json">\n    <meta name="theme-color" content="#0F172A">\n    <script src="https://cdn.tailwindcss.com"></script>\n    <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>\n    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">\n    <style>\n        body { background-color: #F8FAFC; -webkit-tap-highlight-color: transparent; }\n        .tab-content { display: none; }\n        .tab-content.active { display: block; }\n        .hide-scrollbar::-webkit-scrollbar { display: none; }\n        .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }\n    </style>\n</head>\n<body class="text-slate-800 pb-20 md:pb-6">\n\n    <!-- Top App Header -->\n    <header class="bg-slate-900 text-white sticky top-0 z-50 shadow-md">\n        <div class="max-w-6xl mx-auto px-4 py-3 flex justify-between items-center">\n            <div class="flex items-center space-x-3">\n                <div class="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-lg">📱</div>\n                <div>\n                    <h1 id="header-shop-name" class="font-bold text-base md:text-lg leading-tight">My Mobile Shop</h1>\n                    <div class="flex items-center space-x-2 text-xs text-slate-400">\n                        <span class="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>\n                        <span>Supabase Cloud Live</span>\n                    </div>\n                </div>\n            </div>\n            <div class="flex items-center space-x-2">\n                <button onclick="openNewBillModal()" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs md:text-sm font-semibold px-3 py-2 rounded-lg flex items-center shadow">\n                    <i class="fa-solid fa-plus mr-1.5"></i> <span>New Bill</span>\n                </button>\n            </div>\n        </div>\n    </header>\n\n    <!-- Desktop Navigation Bar -->\n    <nav class="hidden md:block bg-white border-b border-slate-200 sticky top-14 z-40">\n        <div class="max-w-6xl mx-auto px-4 flex space-x-1">\n            <button onclick="switchTab(\'dashboard\')" class="nav-btn px-4 py-3 text-sm font-semibold border-b-2 border-blue-600 text-blue-600" data-tab="dashboard"><i class="fa-solid fa-house mr-1.5"></i> Dashboard</button>\n            <button onclick="switchTab(\'products\')" class="nav-btn px-4 py-3 text-sm font-semibold border-b-2 border-transparent text-slate-600 hover:text-slate-900" data-tab="products"><i class="fa-solid fa-box mr-1.5"></i> Products & Stock</button>\n            <button onclick="switchTab(\'sales\')" class="nav-btn px-4 py-3 text-sm font-semibold border-b-2 border-transparent text-slate-600 hover:text-slate-900" data-tab="sales"><i class="fa-solid fa-receipt mr-1.5"></i> Sales Invoices</button>\n            <button onclick="switchTab(\'repairs\')" class="nav-btn px-4 py-3 text-sm font-semibold border-b-2 border-transparent text-slate-600 hover:text-slate-900" data-tab="repairs"><i class="fa-solid fa-wrench mr-1.5"></i> Repairs</button>\n            <button onclick="switchTab(\'customers\')" class="nav-btn px-4 py-3 text-sm font-semibold border-b-2 border-transparent text-slate-600 hover:text-slate-900" data-tab="customers"><i class="fa-solid fa-users mr-1.5"></i> Customers & Udhar</button>\n            <button onclick="switchTab(\'expenses\')" class="nav-btn px-4 py-3 text-sm font-semibold border-b-2 border-transparent text-slate-600 hover:text-slate-900" data-tab="expenses"><i class="fa-solid fa-money-bill-wave mr-1.5"></i> Expenses</button>\n            <button onclick="switchTab(\'settings\')" class="nav-btn px-4 py-3 text-sm font-semibold border-b-2 border-transparent text-slate-600 hover:text-slate-900" data-tab="settings"><i class="fa-solid fa-gear mr-1.5"></i> Settings</button>\n        </div>\n    </nav>\n\n    <!-- Main Content Container -->\n    <main class="max-w-6xl mx-auto p-4">\n\n        <!-- 1. DASHBOARD TAB -->\n        <section id="tab-dashboard" class="tab-content active space-y-4">\n            <!-- Period Selector -->\n            <div class="flex items-center justify-between bg-white p-2.5 rounded-xl border border-slate-200 overflow-x-auto hide-scrollbar space-x-1">\n                <span class="text-xs font-bold text-slate-500 uppercase px-2 hidden sm:inline">Period:</span>\n                <div class="flex space-x-1">\n                    <button onclick="setPeriod(\'today\', this)" class="period-btn px-3 py-1.5 text-xs font-bold rounded-lg bg-blue-600 text-white">Today</button>\n                    <button onclick="setPeriod(\'yesterday\', this)" class="period-btn px-3 py-1.5 text-xs font-bold rounded-lg text-slate-600 hover:bg-slate-100">Yesterday</button>\n                    <button onclick="setPeriod(\'week\', this)" class="period-btn px-3 py-1.5 text-xs font-bold rounded-lg text-slate-600 hover:bg-slate-100">This Week</button>\n                    <button onclick="setPeriod(\'month\', this)" class="period-btn px-3 py-1.5 text-xs font-bold rounded-lg text-slate-600 hover:bg-slate-100">This Month</button>\n                    <button onclick="setPeriod(\'year\', this)" class="period-btn px-3 py-1.5 text-xs font-bold rounded-lg text-slate-600 hover:bg-slate-100">This Year</button>\n                    <button onclick="setPeriod(\'all\', this)" class="period-btn px-3 py-1.5 text-xs font-bold rounded-lg text-slate-600 hover:bg-slate-100">All Time</button>\n                </div>\n            </div>\n\n            <!-- KPI Metric Cards Grid -->\n            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">\n                <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm">\n                    <div class="flex justify-between items-center text-slate-400 text-xs font-semibold">\n                        <span>Sales Revenue</span>\n                        <i class="fa-solid fa-indian-rupee-sign text-blue-600 bg-blue-50 p-1.5 rounded-md"></i>\n                    </div>\n                    <div id="stat-sales" class="text-lg sm:text-xl font-bold text-slate-900 mt-1">₹ 0.00</div>\n                    <div id="stat-sales-count" class="text-[11px] text-slate-500 mt-0.5">0 Invoices</div>\n                </div>\n\n                <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm">\n                    <div class="flex justify-between items-center text-slate-400 text-xs font-semibold">\n                        <span>Repairs Done</span>\n                        <i class="fa-solid fa-wrench text-emerald-600 bg-emerald-50 p-1.5 rounded-md"></i>\n                    </div>\n                    <div id="stat-repairs" class="text-lg sm:text-xl font-bold text-slate-900 mt-1">₹ 0.00</div>\n                    <div id="stat-repairs-count" class="text-[11px] text-slate-500 mt-0.5">0 Repaired</div>\n                </div>\n\n                <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm">\n                    <div class="flex justify-between items-center text-slate-400 text-xs font-semibold">\n                        <span>GST Tax</span>\n                        <i class="fa-solid fa-percent text-purple-600 bg-purple-50 p-1.5 rounded-md"></i>\n                    </div>\n                    <div id="stat-gst" class="text-lg sm:text-xl font-bold text-slate-900 mt-1">₹ 0.00</div>\n                    <div class="text-[11px] text-slate-500 mt-0.5">Tax Collected</div>\n                </div>\n\n                <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm">\n                    <div class="flex justify-between items-center text-slate-400 text-xs font-semibold">\n                        <span>Shop Expenses</span>\n                        <i class="fa-solid fa-arrow-trend-down text-red-600 bg-red-50 p-1.5 rounded-md"></i>\n                    </div>\n                    <div id="stat-expenses" class="text-lg sm:text-xl font-bold text-red-600 mt-1">₹ 0.00</div>\n                    <div class="text-[11px] text-slate-500 mt-0.5">Total Outflow</div>\n                </div>\n\n                <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm col-span-2 sm:col-span-1">\n                    <div class="flex justify-between items-center text-slate-400 text-xs font-semibold">\n                        <span>Customer Udhar</span>\n                        <i class="fa-solid fa-credit-card text-amber-600 bg-amber-50 p-1.5 rounded-md"></i>\n                    </div>\n                    <div id="stat-udhar" class="text-lg sm:text-xl font-bold text-amber-600 mt-1">₹ 0.00</div>\n                    <div class="text-[11px] text-slate-500 mt-0.5">Pending Recovery</div>\n                </div>\n            </div>\n\n            <!-- Quick Stock & Pending Status Banner -->\n            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">\n                <div class="bg-gradient-to-r from-blue-900 to-indigo-900 text-white p-4 rounded-xl shadow flex items-center justify-between">\n                    <div>\n                        <div class="text-xs uppercase tracking-wider text-blue-300 font-bold">Live Inventory</div>\n                        <div id="stat-stock-count" class="text-2xl font-black mt-1">0 Phones</div>\n                        <div id="stat-models-count" class="text-xs text-blue-200">Across 0 distinct models</div>\n                    </div>\n                    <button onclick="switchTab(\'products\')" class="bg-white/10 hover:bg-white/20 px-3 py-2 rounded-lg text-xs font-bold border border-white/20">View Stock →</button>\n                </div>\n\n                <div class="bg-gradient-to-r from-slate-900 to-slate-800 text-white p-4 rounded-xl shadow flex items-center justify-between">\n                    <div>\n                        <div class="text-xs uppercase tracking-wider text-amber-400 font-bold">Repair Workshop</div>\n                        <div id="stat-pending-repairs" class="text-2xl font-black mt-1">0 Pending</div>\n                        <div class="text-xs text-slate-300">Phones in diagnosis / repairing</div>\n                    </div>\n                    <button onclick="switchTab(\'repairs\')" class="bg-white/10 hover:bg-white/20 px-3 py-2 rounded-lg text-xs font-bold border border-white/20">Open Jobs →</button>\n                </div>\n            </div>\n\n            <!-- Recent Invoices & Repairs Split -->\n            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">\n                <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">\n                    <div class="flex justify-between items-center mb-3">\n                        <h2 class="font-bold text-slate-800 text-sm flex items-center"><i class="fa-solid fa-receipt text-blue-600 mr-2"></i> Recent Sales Bills</h2>\n                        <button onclick="switchTab(\'sales\')" class="text-xs font-bold text-blue-600 hover:underline">View All</button>\n                    </div>\n                    <div id="dashboard-recent-sales" class="space-y-2">Loading recent sales...</div>\n                </div>\n\n                <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">\n                    <div class="flex justify-between items-center mb-3">\n                        <h2 class="font-bold text-slate-800 text-sm flex items-center"><i class="fa-solid fa-wrench text-amber-600 mr-2"></i> Recent Repair Tickets</h2>\n                        <button onclick="switchTab(\'repairs\')" class="text-xs font-bold text-blue-600 hover:underline">View All</button>\n                    </div>\n                    <div id="dashboard-recent-repairs" class="space-y-2">Loading recent repairs...</div>\n                </div>\n            </div>\n        </section>\n\n        <!-- 2. PRODUCTS & STOCK TAB -->\n        <section id="tab-products" class="tab-content space-y-3">\n            <div class="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-2">\n                <div class="relative flex-1">\n                    <i class="fa-solid fa-search absolute left-3.5 top-3.5 text-slate-400 text-sm"></i>\n                    <input type="text" id="product-search-input" oninput="loadProducts()" placeholder="Scan IMEI or Search Brand, Model..." class="w-full pl-9 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm outline-none focus:border-blue-600 shadow-sm">\n                </div>\n                <div class="flex space-x-2">\n                    <button onclick="startCameraScanner()" class="bg-slate-800 hover:bg-slate-700 text-white px-3.5 py-2.5 rounded-xl text-sm font-semibold flex items-center justify-center shadow">\n                        <i class="fa-solid fa-camera mr-1.5"></i> <span>Scan Box</span>\n                    </button>\n                    <button onclick="openProductModal()" class="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2.5 rounded-xl text-sm font-semibold flex items-center justify-center shadow">\n                        <i class="fa-solid fa-plus mr-1.5"></i> <span>Add Stock</span>\n                    </button>\n                </div>\n            </div>\n\n            <!-- Live Camera Scanner Box (Hidden by default) -->\n            <div id="camera-scanner-card" class="hidden bg-slate-900 p-4 rounded-xl border border-slate-700 text-center">\n                <div class="flex justify-between items-center text-white mb-2">\n                    <span class="text-xs font-bold uppercase tracking-wider text-blue-400">📷 Point Camera to IMEI Barcode</span>\n                    <button onclick="stopCameraScanner()" class="text-slate-400 hover:text-white text-sm">✕ Close</button>\n                </div>\n                <div id="scanner-reader" class="w-full max-w-sm mx-auto overflow-hidden rounded-lg"></div>\n            </div>\n\n            <div id="products-list-container" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">\n                <!-- Dynamically loaded -->\n            </div>\n        </section>\n\n        <!-- 3. SALES INVOICES TAB -->\n        <section id="tab-sales" class="tab-content space-y-3">\n            <div class="flex justify-between items-center gap-2">\n                <div class="relative flex-1">\n                    <i class="fa-solid fa-search absolute left-3.5 top-3.5 text-slate-400 text-sm"></i>\n                    <input type="text" id="sales-search-input" oninput="loadSales()" placeholder="Search Invoice No or Customer Name..." class="w-full pl-9 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm outline-none focus:border-blue-600 shadow-sm">\n                </div>\n                <button onclick="openNewBillModal()" class="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2.5 rounded-xl text-sm font-semibold flex items-center shadow">\n                    <i class="fa-solid fa-plus mr-1.5"></i> <span>New Bill</span>\n                </button>\n            </div>\n\n            <div id="sales-list-container" class="space-y-2">\n                <!-- Dynamically loaded -->\n            </div>\n        </section>\n\n        <!-- 4. REPAIRS TAB -->\n        <section id="tab-repairs" class="tab-content space-y-3">\n            <div class="flex justify-between items-center gap-2">\n                <div class="relative flex-1">\n                    <i class="fa-solid fa-search absolute left-3.5 top-3.5 text-slate-400 text-sm"></i>\n                    <input type="text" id="repairs-search-input" oninput="loadRepairs()" placeholder="Search Ticket, Phone, or Customer..." class="w-full pl-9 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm outline-none focus:border-blue-600 shadow-sm">\n                </div>\n                <button onclick="openRepairModal()" class="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2.5 rounded-xl text-sm font-semibold flex items-center shadow">\n                    <i class="fa-solid fa-plus mr-1.5"></i> <span>New Repair</span>\n                </button>\n            </div>\n\n            <div id="repairs-list-container" class="space-y-2">\n                <!-- Dynamically loaded -->\n            </div>\n        </section>\n\n        <!-- 5. CUSTOMERS & UDHAR KHATA TAB -->\n        <section id="tab-customers" class="tab-content space-y-3">\n            <div class="flex justify-between items-center gap-2">\n                <div class="relative flex-1">\n                    <i class="fa-solid fa-search absolute left-3.5 top-3.5 text-slate-400 text-sm"></i>\n                    <input type="text" id="customer-search-input" oninput="loadCustomers()" placeholder="Search Customer Name or Phone..." class="w-full pl-9 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm outline-none focus:border-blue-600 shadow-sm">\n                </div>\n                <button onclick="openCustomerModal()" class="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2.5 rounded-xl text-sm font-semibold flex items-center shadow">\n                    <i class="fa-solid fa-plus mr-1.5"></i> <span>Add Customer</span>\n                </button>\n            </div>\n\n            <div id="customers-list-container" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">\n                <!-- Dynamically loaded -->\n            </div>\n        </section>\n\n        <!-- 6. EXPENSES TAB -->\n        <section id="tab-expenses" class="tab-content space-y-3">\n            <div class="flex justify-between items-center">\n                <h2 class="font-bold text-slate-800 text-base">Shop Operational Expenses</h2>\n                <button onclick="openExpenseModal()" class="bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow">\n                    <i class="fa-solid fa-plus mr-1.5"></i> Add Expense\n                </button>\n            </div>\n            <div id="expenses-list-container" class="space-y-2">\n                <!-- Dynamically loaded -->\n            </div>\n        </section>\n\n        <!-- 7. SETTINGS TAB -->\n        <section id="tab-settings" class="tab-content space-y-4">\n            <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">\n                <h2 class="font-bold text-slate-900 text-base border-b border-slate-100 pb-2">🏪 Shop Identity & Invoice Setup</h2>\n                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">\n                    <div>\n                        <label class="block text-xs font-bold text-slate-500 mb-1">Shop Name *</label>\n                        <input type="text" id="set-shop-name" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                    </div>\n                    <div>\n                        <label class="block text-xs font-bold text-slate-500 mb-1">Owner / Manager Name</label>\n                        <input type="text" id="set-owner-name" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                    </div>\n                    <div>\n                        <label class="block text-xs font-bold text-slate-500 mb-1">Contact Mobile Number *</label>\n                        <input type="text" id="set-mobile" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                    </div>\n                    <div>\n                        <label class="block text-xs font-bold text-slate-500 mb-1">Shop Email Address</label>\n                        <input type="text" id="set-email" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                    </div>\n                    <div class="sm:col-span-2">\n                        <label class="block text-xs font-bold text-slate-500 mb-1">Complete Shop Address</label>\n                        <input type="text" id="set-address" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                    </div>\n                    <div>\n                        <label class="block text-xs font-bold text-slate-500 mb-1">GSTIN Number</label>\n                        <input type="text" id="set-gstin" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                    </div>\n                    <div>\n                        <label class="block text-xs font-bold text-slate-500 mb-1">UPI ID for Invoices (e.g. shop@upi)</label>\n                        <input type="text" id="set-upi" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                    </div>\n                </div>\n\n                <h3 class="font-bold text-slate-900 text-sm border-t border-slate-100 pt-3">🏦 Bank Account Details</h3>\n                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">\n                    <div>\n                        <label class="block text-xs font-bold text-slate-500 mb-1">Bank Name</label>\n                        <input type="text" id="set-bank-name" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                    </div>\n                    <div>\n                        <label class="block text-xs font-bold text-slate-500 mb-1">Account Holder</label>\n                        <input type="text" id="set-bank-holder" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                    </div>\n                    <div>\n                        <label class="block text-xs font-bold text-slate-500 mb-1">Account Number</label>\n                        <input type="text" id="set-bank-account" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                    </div>\n                    <div>\n                        <label class="block text-xs font-bold text-slate-500 mb-1">IFSC Code</label>\n                        <input type="text" id="set-bank-ifsc" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                    </div>\n                </div>\n\n                <h3 class="font-bold text-slate-900 text-sm border-t border-slate-100 pt-3">📄 Invoice Terms & Conditions</h3>\n                <div>\n                    <textarea id="set-terms" rows="3" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"></textarea>\n                </div>\n                <div>\n                    <label class="block text-xs font-bold text-slate-500 mb-1">Invoice Footer Note</label>\n                    <input type="text" id="set-footer" class="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                </div>\n\n                <div class="pt-2">\n                    <button onclick="saveSettings()" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-6 py-2.5 rounded-xl text-sm shadow">\n                        💾 Save Settings to Cloud\n                    </button>\n                </div>\n            </div>\n        </section>\n    </main>\n\n    <!-- Mobile Bottom Navigation Bar -->\n    <nav class="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 z-50 flex justify-around items-center py-2 shadow-lg">\n        <button onclick="switchTab(\'dashboard\')" class="mobile-nav-btn flex flex-col items-center text-blue-600" data-tab="dashboard">\n            <i class="fa-solid fa-house text-lg"></i>\n            <span class="text-[10px] font-bold mt-0.5">Home</span>\n        </button>\n        <button onclick="switchTab(\'products\')" class="mobile-nav-btn flex flex-col items-center text-slate-400" data-tab="products">\n            <i class="fa-solid fa-box text-lg"></i>\n            <span class="text-[10px] font-bold mt-0.5">Stock</span>\n        </button>\n        <button onclick="openNewBillModal()" class="flex flex-col items-center -mt-5 bg-emerald-600 text-white w-12 h-12 rounded-full justify-center shadow-lg border-2 border-white">\n            <i class="fa-solid fa-plus text-xl"></i>\n        </button>\n        <button onclick="switchTab(\'repairs\')" class="mobile-nav-btn flex flex-col items-center text-slate-400" data-tab="repairs">\n            <i class="fa-solid fa-wrench text-lg"></i>\n            <span class="text-[10px] font-bold mt-0.5">Repairs</span>\n        </button>\n        <button onclick="switchTab(\'customers\')" class="mobile-nav-btn flex flex-col items-center text-slate-400" data-tab="customers">\n            <i class="fa-solid fa-users text-lg"></i>\n            <span class="text-[10px] font-bold mt-0.5">Udhar</span>\n        </button>\n    </nav>\n\n    <!-- MODAL: NEW BILL / INVOICE -->\n    <div id="modal-new-bill" class="fixed inset-0 bg-slate-900/60 z-50 hidden flex items-center justify-center p-3">\n        <div class="bg-white rounded-2xl max-w-2xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">\n            <div class="px-4 py-3 bg-slate-900 text-white flex justify-between items-center">\n                <h3 class="font-bold text-base flex items-center"><i class="fa-solid fa-receipt text-emerald-400 mr-2"></i> Create Sales Invoice</h3>\n                <button onclick="closeModal(\'modal-new-bill\')" class="text-slate-400 hover:text-white text-lg">✕</button>\n            </div>\n            <div class="p-4 overflow-y-auto space-y-3 flex-1">\n                <!-- Customer selection -->\n                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">\n                    <div>\n                        <label class="block text-xs font-bold text-slate-500 mb-1">Customer Name *</label>\n                        <input type="text" id="bill-cust-name" placeholder="Walk-in Customer / Type Name" class="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                    </div>\n                    <div>\n                        <label class="block text-xs font-bold text-slate-500 mb-1">Customer Phone Number</label>\n                        <input type="text" id="bill-cust-phone" placeholder="10-digit mobile" class="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-sm">\n                    </div>\n                </div>\n\n                <!-- Product Add Line -->\n                <div class="bg-blue-50 p-3 rounded-xl border border-blue-200 space-y-2">\n                    <div class="text-xs font-bold text-blue-900 uppercase">Add Item to Cart</div>\n                    <div class="grid grid-cols-1 sm:grid-cols-12 gap-2">\n                        <div class="sm:col-span-6">\n                            <input type="text" id="bill-prod-search" oninput="suggestBillProducts(this.value)" placeholder="Search stock or type item name..." class="w-full p-2 bg-white border border-blue-300 rounded-lg text-sm">\n                            <div id="bill-prod-suggestions" class="hidden bg-white border border-slate-200 rounded-lg mt-1 max-h-40 overflow-y-auto shadow-lg text-xs"></div>\n                        </div>\n                        <div class="sm:col-span-2">\n                            <input type="number" id="bill-prod-qty" value="1" min="1" placeholder="Qty" class="w-full p-2 bg-white border border-blue-300 rounded-lg text-sm text-center">\n                        </div>\n                        <div class="sm:col-span-2">\n                            <input type="number" id="bill-prod-rate" placeholder="Rate ₹" class="w-full p-2 bg-white border border-blue-300 rounded-lg text-sm">\n                        </div>\n                        <div class="sm:col-span-2">\n                            <button onclick="addItemToCart()" class="w-full bg-blue-600 text-white font-bold p-2 rounded-lg text-sm hover:bg-blue-500">+ Add</button>\n                        </div>\n                    </div>\n                </div>\n\n                <!-- Cart Items Table -->\n                <div class="border border-slate-200 rounded-xl overflow-hidden">\n                    <table class="w-full text-left text-xs">\n                        <thead class="bg-slate-100 text-slate-600 font-bold">\n                            <tr>\n                                <th class="p-2">Item Description</th>\n                                <th class="p-2 text-center">Qty</th>\n                                <th class="p-2 text-right">Rate</th>\n                                <th class="p-2 text-right">Total</th>\n                                <th class="p-2 text-center">Action</th>\n                            </tr>\n                        </thead>\n                        <tbody id="cart-table-body">\n                            <tr><td colspan="5" class="text-center p-4 text-slate-400">Cart is empty. Add products above.</td></tr>\n                        </tbody>\n                    </table>\n                </div>\n\n                <!-- Bill Totals & Payment Modes -->\n                <div class="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-2">\n                    <div class="flex justify-between font-bold text-sm text-slate-800">\n                        <span>Grand Total:</span>\n                        <span id="bill-grand-total" class="text-blue-600 text-base">₹ 0.00</span>\n                    </div>\n\n                    <div class="text-xs font-bold text-slate-500 pt-1">Payment Received:</div>\n                    <div class="grid grid-cols-3 sm:grid-cols-5 gap-2">\n                        <div>\n                            <label class="text-[10px] text-slate-400 font-bold block">Cash ₹</label>\n                            <input type="number" id="pay-cash" value="0" class="w-full p-1.5 border border-slate-300 rounded text-xs text-center">\n                        </div>\n                        <div>\n                            <label class="text-[10px] text-slate-400 font-bold block">UPI ₹</label>\n                            <input type="number" id="pay-upi" value="0" class="w-full p-1.5 border border-slate-300 rounded text-xs text-center">\n                        </div>\n                        <div>\n                            <label class="text-[10px] text-slate-400 font-bold block">Bank ₹</label>\n                            <input type="number" id="pay-bank" value="0" class="w-full p-1.5 border border-slate-300 rounded text-xs text-center">\n                        </div>\n                        <div>\n                            <label class="text-[10px] text-slate-400 font-bold block">Card ₹</label>\n                            <input type="number" id="pay-card" value="0" class="w-full p-1.5 border border-slate-300 rounded text-xs text-center">\n                        </div>\n                        <div class="col-span-2 sm:col-span-1">\n                            <label class="text-[10px] text-red-500 font-bold block">Udhar ₹</label>\n                            <input type="number" id="pay-udhar" value="0" class="w-full p-1.5 border border-red-300 rounded text-xs text-center text-red-600 font-bold">\n                        </div>\n                    </div>\n                </div>\n            </div>\n            <div class="p-3 bg-slate-100 border-t border-slate-200 flex justify-end space-x-2">\n                <button onclick="closeModal(\'modal-new-bill\')" class="px-4 py-2 bg-slate-300 text-slate-700 font-bold rounded-xl text-xs">Cancel</button>\n                <button onclick="saveBill()" class="px-6 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs shadow">💾 Save & Print Bill</button>\n            </div>\n        </div>\n    </div>\n\n    <!-- MODAL: ADD PRODUCT -->\n    <div id="modal-product" class="fixed inset-0 bg-slate-900/60 z-50 hidden flex items-center justify-center p-3">\n        <div class="bg-white rounded-2xl max-w-lg w-full p-5 shadow-2xl space-y-3">\n            <h3 class="font-bold text-base text-slate-900 border-b border-slate-100 pb-2">📦 Add Product / Phone Stock</h3>\n            <div class="grid grid-cols-2 gap-2 text-xs">\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Brand *</label>\n                    <input type="text" id="prod-brand" placeholder="Samsung / Vivo / Apple" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Model Name *</label>\n                    <input type="text" id="prod-model" placeholder="Galaxy S23 / Y200" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">IMEI 1 / Barcode</label>\n                    <input type="text" id="prod-imei1" placeholder="15-digit IMEI" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">IMEI 2</label>\n                    <input type="text" id="prod-imei2" placeholder="Secondary IMEI" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">RAM & Storage</label>\n                    <input type="text" id="prod-specs" placeholder="8GB / 128GB" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Color</label>\n                    <input type="text" id="prod-color" placeholder="Black / Blue" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Purchase Price ₹</label>\n                    <input type="number" id="prod-purchase" placeholder="0.00" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Sale Price ₹ *</label>\n                    <input type="number" id="prod-sale" placeholder="0.00" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">GST %</label>\n                    <input type="number" id="prod-gst" value="18" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Stock Qty *</label>\n                    <input type="number" id="prod-stock" value="1" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n            </div>\n            <div class="flex justify-end space-x-2 pt-2 border-t border-slate-100">\n                <button onclick="closeModal(\'modal-product\')" class="px-4 py-2 bg-slate-200 text-slate-700 font-bold rounded-lg text-xs">Cancel</button>\n                <button onclick="saveProduct()" class="px-5 py-2 bg-blue-600 text-white font-bold rounded-lg text-xs shadow">Save Stock</button>\n            </div>\n        </div>\n    </div>\n\n    <!-- MODAL: ADD REPAIR -->\n    <div id="modal-repair" class="fixed inset-0 bg-slate-900/60 z-50 hidden flex items-center justify-center p-3">\n        <div class="bg-white rounded-2xl max-w-lg w-full p-5 shadow-2xl space-y-3">\n            <h3 class="font-bold text-base text-slate-900 border-b border-slate-100 pb-2">🔧 Create Repair Ticket</h3>\n            <div class="grid grid-cols-2 gap-2 text-xs">\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Customer Name *</label>\n                    <input type="text" id="rep-cust" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Mobile Number</label>\n                    <input type="text" id="rep-mobile" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Phone Model</label>\n                    <input type="text" id="rep-model" placeholder="e.g. Redmi Note 10" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Problem Description *</label>\n                    <input type="text" id="rep-problem" placeholder="Display / Charging / Dead" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Final Amount ₹</label>\n                    <input type="number" id="rep-final" placeholder="0.00" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Advance Paid ₹</label>\n                    <input type="number" id="rep-advance" value="0" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n            </div>\n            <div class="flex justify-end space-x-2 pt-2 border-t border-slate-100">\n                <button onclick="closeModal(\'modal-repair\')" class="px-4 py-2 bg-slate-200 text-slate-700 font-bold rounded-lg text-xs">Cancel</button>\n                <button onclick="saveRepair()" class="px-5 py-2 bg-amber-600 text-white font-bold rounded-lg text-xs shadow">Save Ticket</button>\n            </div>\n        </div>\n    </div>\n\n    <!-- MODAL: ADD CUSTOMER -->\n    <div id="modal-customer" class="fixed inset-0 bg-slate-900/60 z-50 hidden flex items-center justify-center p-3">\n        <div class="bg-white rounded-2xl max-w-sm w-full p-5 shadow-2xl space-y-3">\n            <h3 class="font-bold text-base text-slate-900 border-b border-slate-100 pb-2">👤 Add Customer Profile</h3>\n            <div class="space-y-2 text-xs">\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Customer Name *</label>\n                    <input type="text" id="cust-name" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Mobile Number</label>\n                    <input type="text" id="cust-phone" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Opening Udhar / Balance ₹</label>\n                    <input type="number" id="cust-bal" value="0" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n            </div>\n            <div class="flex justify-end space-x-2 pt-2 border-t border-slate-100">\n                <button onclick="closeModal(\'modal-customer\')" class="px-4 py-2 bg-slate-200 text-slate-700 font-bold rounded-lg text-xs">Cancel</button>\n                <button onclick="saveCustomer()" class="px-5 py-2 bg-blue-600 text-white font-bold rounded-lg text-xs shadow">Save Customer</button>\n            </div>\n        </div>\n    </div>\n\n    <!-- MODAL: ADD EXPENSE -->\n    <div id="modal-expense" class="fixed inset-0 bg-slate-900/60 z-50 hidden flex items-center justify-center p-3">\n        <div class="bg-white rounded-2xl max-w-sm w-full p-5 shadow-2xl space-y-3">\n            <h3 class="font-bold text-base text-slate-900 border-b border-slate-100 pb-2">💸 Add Shop Expense</h3>\n            <div class="space-y-2 text-xs">\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Category *</label>\n                    <input type="text" id="exp-cat" placeholder="Rent / Tea / Electricity" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Description</label>\n                    <input type="text" id="exp-desc" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n                <div>\n                    <label class="font-bold text-slate-500 block mb-1">Amount ₹ *</label>\n                    <input type="number" id="exp-amt" class="w-full p-2 border border-slate-200 rounded-lg">\n                </div>\n            </div>\n            <div class="flex justify-end space-x-2 pt-2 border-t border-slate-100">\n                <button onclick="closeModal(\'modal-expense\')" class="px-4 py-2 bg-slate-200 text-slate-700 font-bold rounded-lg text-xs">Cancel</button>\n                <button onclick="saveExpense()" class="px-5 py-2 bg-red-600 text-white font-bold rounded-lg text-xs shadow">Save Expense</button>\n            </div>\n        </div>\n    </div>\n\n    <!-- Application Core Script -->\n    <script>\n        let currentPeriod = \'today\';\n        let currentCart = [];\n        let html5QrScanner = null;\n        let allStockProducts = [];\n\n        function formatMoney(n) {\n            return \'₹ \' + Number(n || 0).toLocaleString(\'en-IN\', {minimumFractionDigits: 2, maximumFractionDigits: 2});\n        }\n\n        function switchTab(tabId) {\n            document.querySelectorAll(\'.tab-content\').forEach(t => t.classList.remove(\'active\'));\n            const target = document.getElementById(\'tab-\' + tabId);\n            if(target) target.classList.add(\'active\');\n\n            // Update Desktop Nav\n            document.querySelectorAll(\'.nav-btn\').forEach(btn => {\n                const isActive = btn.getAttribute(\'data-tab\') === tabId;\n                btn.className = `nav-btn px-4 py-3 text-sm font-semibold border-b-2 ${isActive ? \'border-blue-600 text-blue-600\' : \'border-transparent text-slate-600 hover:text-slate-900\'}`;\n            });\n\n            // Update Mobile Nav\n            document.querySelectorAll(\'.mobile-nav-btn\').forEach(btn => {\n                const isActive = btn.getAttribute(\'data-tab\') === tabId;\n                btn.className = `mobile-nav-btn flex flex-col items-center ${isActive ? \'text-blue-600\' : \'text-slate-400\'}`;\n            });\n\n            if(tabId === \'dashboard\') loadDashboard();\n            else if(tabId === \'products\') loadProducts();\n            else if(tabId === \'sales\') loadSales();\n            else if(tabId === \'repairs\') loadRepairs();\n            else if(tabId === \'customers\') loadCustomers();\n            else if(tabId === \'expenses\') loadExpenses();\n            else if(tabId === \'settings\') loadSettings();\n        }\n\n        function setPeriod(p, btn) {\n            currentPeriod = p;\n            document.querySelectorAll(\'.period-btn\').forEach(b => b.className = \'period-btn px-3 py-1.5 text-xs font-bold rounded-lg text-slate-600 hover:bg-slate-100\');\n            btn.className = \'period-btn px-3 py-1.5 text-xs font-bold rounded-lg bg-blue-600 text-white\';\n            loadDashboard();\n        }\n\n        function closeModal(id) {\n            document.getElementById(id).classList.add(\'hidden\');\n        }\n\n        // ---------- 1. DASHBOARD ----------\n        async function loadDashboard() {\n            try {\n                const res = await fetch(`/api/dashboard?period=${currentPeriod}`);\n                const d = await res.json();\n\n                document.getElementById(\'stat-sales\').innerText = formatMoney(d.sales_total);\n                document.getElementById(\'stat-sales-count\').innerText = `${d.sales_count} Invoices`;\n                document.getElementById(\'stat-repairs\').innerText = formatMoney(d.repairs_total);\n                document.getElementById(\'stat-repairs-count\').innerText = `${d.repairs_count} Repaired`;\n                document.getElementById(\'stat-gst\').innerText = formatMoney(d.gst_total);\n                document.getElementById(\'stat-expenses\').innerText = formatMoney(d.expenses_total);\n                document.getElementById(\'stat-udhar\').innerText = formatMoney(d.udhar_total);\n                document.getElementById(\'stat-stock-count\').innerText = `${d.total_stock} Phones`;\n                document.getElementById(\'stat-models-count\').innerText = `Across ${d.total_models} models`;\n                document.getElementById(\'stat-pending-repairs\').innerText = `${d.pending_repairs} Pending`;\n\n                // Recent Sales\n                const sContainer = document.getElementById(\'dashboard-recent-sales\');\n                if(!d.recent_sales || d.recent_sales.length === 0) {\n                    sContainer.innerHTML = \'<div class="text-xs text-slate-400 text-center py-4">No recent sales.</div>\';\n                } else {\n                    sContainer.innerHTML = d.recent_sales.map(s => `\n                        <div class="flex justify-between items-center p-2.5 bg-slate-50 hover:bg-blue-50/50 rounded-lg border border-slate-100 text-xs">\n                            <div>\n                                <div class="font-bold text-slate-800">${s.invoice_no}</div>\n                                <div class="text-slate-500">${s.customer_name || \'Walk-in\'} • ${s.created_at.split(\' \')[0]}</div>\n                            </div>\n                            <div class="text-right">\n                                <div class="font-bold text-blue-600">${formatMoney(s.grand_total)}</div>\n                                <a href="/invoice/${s.invoice_no}" target="_blank" class="text-[11px] text-blue-500 hover:underline">View Bill →</a>\n                            </div>\n                        </div>\n                    `).join(\'\');\n                }\n\n                // Recent Repairs\n                const rContainer = document.getElementById(\'dashboard-recent-repairs\');\n                if(!d.recent_repairs || d.recent_repairs.length === 0) {\n                    rContainer.innerHTML = \'<div class="text-xs text-slate-400 text-center py-4">No recent repair tickets.</div>\';\n                } else {\n                    rContainer.innerHTML = d.recent_repairs.map(r => `\n                        <div class="flex justify-between items-center p-2.5 bg-slate-50 hover:bg-amber-50/50 rounded-lg border border-slate-100 text-xs">\n                            <div>\n                                <div class="font-bold text-slate-800">${r.phone_model} - ${r.customer}</div>\n                                <div class="text-slate-500">${r.problem} • ${r.repair_no}</div>\n                            </div>\n                            <div class="text-right">\n                                <span class="inline-block px-2 py-0.5 rounded text-[10px] font-bold ${r.status === \'Delivered\' ? \'bg-emerald-100 text-emerald-700\' : \'bg-amber-100 text-amber-700\'}">${r.status || \'Received\'}</span>\n                                <div class="font-bold text-slate-700 mt-0.5">${formatMoney(r.final_amount)}</div>\n                            </div>\n                        </div>\n                    `).join(\'\');\n                }\n            } catch(e) {\n                console.error(e);\n            }\n        }\n\n        // ---------- 2. PRODUCTS & STOCK ----------\n        async function loadProducts() {\n            const q = document.getElementById(\'product-search-input\').value;\n            const res = await fetch(`/api/products?q=${encodeURIComponent(q)}`);\n            const items = await res.json();\n            allStockProducts = items;\n\n            const c = document.getElementById(\'products-list-container\');\n            if(items.length === 0) {\n                c.innerHTML = \'<div class="col-span-full text-center py-8 text-slate-400 text-sm">No products found.</div>\';\n                return;\n            }\n\n            c.innerHTML = items.map(p => `\n                <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">\n                    <div>\n                        <div class="flex justify-between items-start">\n                            <h3 class="font-bold text-slate-900 text-sm">${p.brand} ${p.model}</h3>\n                            <span class="px-2 py-0.5 rounded-full text-xs font-bold ${p.stock > 0 ? \'bg-emerald-100 text-emerald-700\' : \'bg-red-100 text-red-700\'}">\n                                ${p.stock > 0 ? p.stock + \' in Stock\' : \'Out of Stock\'}\n                            </span>\n                        </div>\n                        <div class="text-xs text-slate-500 mt-1">\n                            ${p.ram ? p.ram + \' RAM • \' : \'\'}${p.storage ? p.storage + \' • \' : \'\'}${p.color || \'\'}\n                        </div>\n                        <div class="text-xs text-slate-400 mt-1">\n                            IMEI: <span class="font-mono text-slate-700 font-bold">${p.imei1 || \'N/A\'}</span>\n                        </div>\n                    </div>\n                    <div class="flex justify-between items-center mt-4 pt-3 border-t border-slate-100">\n                        <div>\n                            <div class="text-[10px] text-slate-400 uppercase font-bold">Sale Price</div>\n                            <div class="text-base font-black text-blue-600">${formatMoney(p.sale_price)}</div>\n                        </div>\n                        <button onclick="quickSell(\'${p.id}\', \'${p.brand} ${p.model}\', \'${p.imei1 || \'\'}\', ${p.sale_price}, ${p.gst || 18})" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow">\n                            ⚡ Sell Now\n                        </button>\n                    </div>\n                </div>\n            `).join(\'\');\n        }\n\n        function openProductModal() {\n            document.getElementById(\'modal-product\').classList.remove(\'hidden\');\n        }\n\n        async function saveProduct() {\n            const data = {\n                brand: document.getElementById(\'prod-brand\').value.trim(),\n                model: document.getElementById(\'prod-model\').value.trim(),\n                imei1: document.getElementById(\'prod-imei1\').value.trim(),\n                imei2: document.getElementById(\'prod-imei2\').value.trim(),\n                specs: document.getElementById(\'prod-specs\').value.trim(),\n                color: document.getElementById(\'prod-color\').value.trim(),\n                purchase_price: document.getElementById(\'prod-purchase\').value,\n                sale_price: document.getElementById(\'prod-sale\').value,\n                gst: document.getElementById(\'prod-gst\').value,\n                stock: document.getElementById(\'prod-stock\').value\n            };\n            if(!data.brand || !data.model || !data.sale_price) {\n                alert("Please fill Brand, Model and Sale Price.");\n                return;\n            }\n            await fetch(\'/api/products\', {\n                method: \'POST\',\n                headers: {\'Content-Type\': \'application/json\'},\n                body: JSON.stringify(data)\n            });\n            closeModal(\'modal-product\');\n            loadProducts();\n        }\n\n        // ---------- CAMERA SCANNER ----------\n        function startCameraScanner() {\n            const card = document.getElementById(\'camera-scanner-card\');\n            card.classList.remove(\'hidden\');\n            html5QrScanner = new Html5Qrcode("scanner-reader");\n            html5QrScanner.start(\n                { facingMode: "environment" },\n                { fps: 10, qrbox: { width: 250, height: 150 } },\n                (decodedText) => {\n                    document.getElementById(\'product-search-input\').value = decodedText;\n                    loadProducts();\n                    stopCameraScanner();\n                },\n                (errorMessage) => {}\n            ).catch(err => alert("Camera permission error: " + err));\n        }\n\n        function stopCameraScanner() {\n            if(html5QrScanner) {\n                html5QrScanner.stop().then(() => {\n                    document.getElementById(\'camera-scanner-card\').classList.add(\'hidden\');\n                });\n            } else {\n                document.getElementById(\'camera-scanner-card\').classList.add(\'hidden\');\n            }\n        }\n\n        // ---------- 3. SALES & BILLING ----------\n        async function loadSales() {\n            const q = document.getElementById(\'sales-search-input\').value;\n            const res = await fetch(`/api/sales?q=${encodeURIComponent(q)}`);\n            const items = await res.json();\n            const c = document.getElementById(\'sales-list-container\');\n            if(items.length === 0) {\n                c.innerHTML = \'<div class="text-center py-8 text-slate-400 text-sm">No sales invoices found.</div>\';\n                return;\n            }\n            c.innerHTML = items.map(s => `\n                <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">\n                    <div>\n                        <div class="flex items-center space-x-2">\n                            <span class="font-bold text-slate-900 text-sm">${s.invoice_no}</span>\n                            <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">${s.sale_type || \'GST\'}</span>\n                        </div>\n                        <div class="text-xs text-slate-500 mt-0.5">👤 ${s.customer_name || \'Walk-in Customer\'} • 📅 ${s.created_at}</div>\n                    </div>\n                    <div class="flex items-center space-x-2 w-full sm:w-auto justify-between sm:justify-end">\n                        <div class="text-base font-black text-blue-600">${formatMoney(s.grand_total)}</div>\n                        <a href="/invoice/${s.invoice_no}" target="_blank" class="bg-blue-50 hover:bg-blue-100 text-blue-600 text-xs font-bold px-3 py-1.5 rounded-lg border border-blue-200">\n                            📄 View Bill\n                        </a>\n                        <button onclick="shareWhatsApp(\'${s.invoice_no}\', \'${s.customer_name || \'\'}\', ${s.grand_total})" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg">\n                            <i class="fa-brands fa-whatsapp"></i> WhatsApp\n                        </button>\n                    </div>\n                </div>\n            `).join(\'\');\n        }\n\n        function openNewBillModal() {\n            currentCart = [];\n            renderCart();\n            document.getElementById(\'modal-new-bill\').classList.remove(\'hidden\');\n        }\n\n        function quickSell(pid, name, imei, price, gst) {\n            openNewBillModal();\n            currentCart.push({\n                pid: pid,\n                name: name,\n                imei: imei,\n                qty: 1,\n                rate: price,\n                gst: gst,\n                taxable: price,\n                gstamt: (price * gst / 100),\n                amount: price + (price * gst / 100)\n            });\n            renderCart();\n        }\n\n        function suggestBillProducts(q) {\n            const sug = document.getElementById(\'bill-prod-suggestions\');\n            if(!q) { sug.classList.add(\'hidden\'); return; }\n            const matches = allStockProducts.filter(p => (p.brand + \' \' + p.model + \' \' + p.imei1).toLowerCase().includes(q.toLowerCase())).slice(0, 6);\n            if(matches.length === 0) { sug.classList.add(\'hidden\'); return; }\n            sug.innerHTML = matches.map(p => `\n                <div onclick="selectBillProduct(\'${p.id}\', \'${p.brand} ${p.model}\', \'${p.imei1 || \'\'}\', ${p.sale_price}, ${p.gst || 18})" class="p-2 hover:bg-blue-50 cursor-pointer border-b border-slate-100">\n                    <span class="font-bold text-slate-800">${p.brand} ${p.model}</span> (IMEI: ${p.imei1 || \'N/A\'}) - <span class="text-blue-600 font-bold">₹${p.sale_price}</span>\n                </div>\n            `).join(\'\');\n            sug.classList.remove(\'hidden\');\n        }\n\n        let selectedProductForBill = null;\n        function selectBillProduct(pid, name, imei, rate, gst) {\n            selectedProductForBill = { pid, name, imei, rate, gst };\n            document.getElementById(\'bill-prod-search\').value = `${name} [${imei || \'No IMEI\'}]`;\n            document.getElementById(\'bill-prod-rate\').value = rate;\n            document.getElementById(\'bill-prod-suggestions\').classList.add(\'hidden\');\n        }\n\n        function addItemToCart() {\n            const nameInput = document.getElementById(\'bill-prod-search\').value.trim();\n            const qty = parseInt(document.getElementById(\'bill-prod-qty\').value || 1);\n            const rate = parseFloat(document.getElementById(\'bill-prod-rate\').value || 0);\n            if(!nameInput || rate <= 0) {\n                alert("Please enter product description and valid rate.");\n                return;\n            }\n            const taxable = qty * rate;\n            const gstamt = (taxable * 18 / 100);\n            currentCart.push({\n                pid: selectedProductForBill ? selectedProductForBill.pid : null,\n                name: selectedProductForBill ? selectedProductForBill.name : nameInput,\n                imei: selectedProductForBill ? selectedProductForBill.imei : \'\',\n                qty: qty,\n                rate: rate,\n                gst: 18,\n                taxable: taxable,\n                gstamt: gstamt,\n                amount: taxable + gstamt\n            });\n            document.getElementById(\'bill-prod-search\').value = \'\';\n            document.getElementById(\'bill-prod-rate\').value = \'\';\n            selectedProductForBill = null;\n            renderCart();\n        }\n\n        function removeCartItem(idx) {\n            currentCart.splice(idx, 1);\n            renderCart();\n        }\n\n        function renderCart() {\n            const tbody = document.getElementById(\'cart-table-body\');\n            if(currentCart.length === 0) {\n                tbody.innerHTML = \'<tr><td colspan="5" class="text-center p-4 text-slate-400">Cart is empty. Add products above.</td></tr>\';\n                document.getElementById(\'bill-grand-total\').innerText = \'₹ 0.00\';\n                document.getElementById(\'pay-cash\').value = \'0\';\n                return;\n            }\n            let total = 0;\n            tbody.innerHTML = currentCart.map((it, idx) => {\n                total += it.amount;\n                return `\n                    <tr class="border-b border-slate-100">\n                        <td class="p-2 font-semibold text-slate-800">${it.name} ${it.imei ? \'<br><span class="text-[10px] text-slate-400">IMEI: \' + it.imei + \'</span>\' : \'\'}</td>\n                        <td class="p-2 text-center">${it.qty}</td>\n                        <td class="p-2 text-right">₹${it.rate.toFixed(2)}</td>\n                        <td class="p-2 text-right font-bold text-slate-900">₹${it.amount.toFixed(2)}</td>\n                        <td class="p-2 text-center"><button onclick="removeCartItem(${idx})" class="text-red-500 hover:text-red-700">✕</button></td>\n                    </tr>\n                `;\n            }).join(\'\');\n            document.getElementById(\'bill-grand-total\').innerText = formatMoney(total);\n            document.getElementById(\'pay-cash\').value = total.toFixed(2);\n        }\n\n        async function saveBill() {\n            if(currentCart.length === 0) {\n                alert("Cart is empty.");\n                return;\n            }\n            const total = currentCart.reduce((sum, it) => sum + it.amount, 0);\n            const subtotal = currentCart.reduce((sum, it) => sum + it.taxable, 0);\n            const gst_amt = currentCart.reduce((sum, it) => sum + it.gstamt, 0);\n\n            const cash = parseFloat(document.getElementById(\'pay-cash\').value || 0);\n            const upi = parseFloat(document.getElementById(\'pay-upi\').value || 0);\n            const bank = parseFloat(document.getElementById(\'pay-bank\').value || 0);\n            const card = parseFloat(document.getElementById(\'pay-card\').value || 0);\n            const udhar = parseFloat(document.getElementById(\'pay-udhar\').value || 0);\n\n            if(Math.round(cash + upi + bank + card + udhar) !== Math.round(total)) {\n                alert(`Payment mismatch: Total is ₹${total.toFixed(2)} but payments sum to ₹${(cash+upi+bank+card+udhar).toFixed(2)}`);\n                return;\n            }\n\n            const payload = {\n                customer_name: document.getElementById(\'bill-cust-name\').value.trim() || \'Walk-in Customer\',\n                customer_phone: document.getElementById(\'bill-cust-phone\').value.trim(),\n                sale_type: \'GST\',\n                subtotal: subtotal,\n                gst_amount: gst_amt,\n                grand_total: total,\n                cash: cash,\n                upi: upi,\n                bank: bank,\n                card: card,\n                udhar: udhar,\n                items: currentCart\n            };\n\n            const res = await fetch(\'/api/sales\', {\n                method: \'POST\',\n                headers: {\'Content-Type\': \'application/json\'},\n                body: JSON.stringify(payload)\n            });\n            const data = await res.json();\n            if(data.success) {\n                closeModal(\'modal-new-bill\');\n                window.open(`/invoice/${data.invoice_no}`, \'_blank\');\n                loadSales();\n                loadDashboard();\n            } else {\n                alert("Error saving bill: " + data.error);\n            }\n        }\n\n        function shareWhatsApp(invNo, custName, total) {\n            const shopName = document.getElementById(\'header-shop-name\').innerText;\n            const msg = `Hello ${custName || \'Customer\'},\\nThank you for shopping at *${shopName}*!\\n\\n📄 *Invoice No:* ${invNo}\\n💰 *Total Amount:* ₹${Number(total).toLocaleString(\'en-IN\')}\\n\\nView and Download your Tax Invoice here:\\n${window.location.origin}/invoice/${invNo}`;\n            window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(msg)}`, \'_blank\');\n        }\n\n        // ---------- 4. REPAIRS ----------\n        async function loadRepairs() {\n            const q = document.getElementById(\'repairs-search-input\').value;\n            const res = await fetch(`/api/repairs?q=${encodeURIComponent(q)}`);\n            const items = await res.json();\n            const c = document.getElementById(\'repairs-list-container\');\n            if(items.length === 0) {\n                c.innerHTML = \'<div class="text-center py-8 text-slate-400 text-sm">No repair tickets found.</div>\';\n                return;\n            }\n            c.innerHTML = items.map(r => `\n                <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">\n                    <div>\n                        <div class="flex items-center space-x-2">\n                            <span class="font-bold text-slate-900 text-sm">${r.phone_model} - ${r.customer}</span>\n                            <span class="text-[10px] font-bold px-2 py-0.5 rounded ${r.status === \'Delivered\' ? \'bg-emerald-100 text-emerald-700\' : \'bg-amber-100 text-amber-700\'}">${r.status || \'Received\'}</span>\n                        </div>\n                        <div class="text-xs text-slate-500 mt-0.5">Problem: <span class="font-semibold text-slate-700">${r.problem}</span> • Ticket: ${r.repair_no} • 📞 ${r.mobile || \'No Mobile\'}</div>\n                    </div>\n                    <div class="flex items-center space-x-3">\n                        <div class="text-right">\n                            <div class="text-xs text-slate-400">Final: ${formatMoney(r.final_amount)}</div>\n                            <div class="text-xs font-bold text-red-600">Pending: ${formatMoney(r.pending)}</div>\n                        </div>\n                    </div>\n                </div>\n            `).join(\'\');\n        }\n\n        function openRepairModal() {\n            document.getElementById(\'modal-repair\').classList.remove(\'hidden\');\n        }\n\n        async function saveRepair() {\n            const data = {\n                customer: document.getElementById(\'rep-cust\').value.trim(),\n                mobile: document.getElementById(\'rep-mobile\').value.trim(),\n                phone_model: document.getElementById(\'rep-model\').value.trim(),\n                problem: document.getElementById(\'rep-problem\').value.trim(),\n                final_amount: document.getElementById(\'rep-final\').value,\n                advance: document.getElementById(\'rep-advance\').value\n            };\n            if(!data.customer || !data.problem) {\n                alert("Please fill Customer Name and Problem Description.");\n                return;\n            }\n            await fetch(\'/api/repairs\', {\n                method: \'POST\',\n                headers: {\'Content-Type\': \'application/json\'},\n                body: JSON.stringify(data)\n            });\n            closeModal(\'modal-repair\');\n            loadRepairs();\n        }\n\n        // ---------- 5. CUSTOMERS ----------\n        async function loadCustomers() {\n            const q = document.getElementById(\'customer-search-input\').value;\n            const res = await fetch(`/api/customers?q=${encodeURIComponent(q)}`);\n            const items = await res.json();\n            const c = document.getElementById(\'customers-list-container\');\n            if(items.length === 0) {\n                c.innerHTML = \'<div class="col-span-full text-center py-8 text-slate-400 text-sm">No customers found.</div>\';\n                return;\n            }\n            c.innerHTML = items.map(cust => `\n                <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex justify-between items-center">\n                    <div>\n                        <div class="font-bold text-slate-900 text-sm">👤 ${cust.name}</div>\n                        <div class="text-xs text-slate-500 mt-0.5">📞 ${cust.mobile || \'No Mobile\'}</div>\n                    </div>\n                    <div class="text-right">\n                        <div class="text-[10px] text-slate-400 uppercase font-bold">Udhar Balance</div>\n                        <div class="text-base font-black ${cust.opening_balance > 0 ? \'text-red-600\' : \'text-emerald-600\'}">${formatMoney(cust.opening_balance)}</div>\n                    </div>\n                </div>\n            `).join(\'\');\n        }\n\n        function openCustomerModal() {\n            document.getElementById(\'modal-customer\').classList.remove(\'hidden\');\n        }\n\n        async function saveCustomer() {\n            const data = {\n                name: document.getElementById(\'cust-name\').value.trim(),\n                mobile: document.getElementById(\'cust-phone\').value.trim(),\n                opening_balance: document.getElementById(\'cust-bal\').value\n            };\n            if(!data.name) { alert("Customer Name is required."); return; }\n            await fetch(\'/api/customers\', {\n                method: \'POST\',\n                headers: {\'Content-Type\': \'application/json\'},\n                body: JSON.stringify(data)\n            });\n            closeModal(\'modal-customer\');\n            loadCustomers();\n        }\n\n        // ---------- 6. EXPENSES ----------\n        async function loadExpenses() {\n            const res = await fetch(\'/api/expenses\');\n            const items = await res.json();\n            const c = document.getElementById(\'expenses-list-container\');\n            if(items.length === 0) {\n                c.innerHTML = \'<div class="text-center py-8 text-slate-400 text-sm">No expenses logged.</div>\';\n                return;\n            }\n            c.innerHTML = items.map(e => `\n                <div class="bg-white p-3 rounded-xl border border-slate-200 shadow-sm flex justify-between items-center text-xs">\n                    <div>\n                        <div class="font-bold text-slate-800">${e.category}</div>\n                        <div class="text-slate-500">${e.description || \'\'} • 📅 ${e.created_at}</div>\n                    </div>\n                    <div class="font-bold text-red-600 text-sm">${formatMoney(e.amount)}</div>\n                </div>\n            `).join(\'\');\n        }\n\n        function openExpenseModal() {\n            document.getElementById(\'modal-expense\').classList.remove(\'hidden\');\n        }\n\n        async function saveExpense() {\n            const data = {\n                category: document.getElementById(\'exp-cat\').value.trim(),\n                description: document.getElementById(\'exp-desc\').value.trim(),\n                amount: document.getElementById(\'exp-amt\').value\n            };\n            if(!data.category || !data.amount) { alert("Category and Amount required."); return; }\n            await fetch(\'/api/expenses\', {\n                method: \'POST\',\n                headers: {\'Content-Type\': \'application/json\'},\n                body: JSON.stringify(data)\n            });\n            closeModal(\'modal-expense\');\n            loadExpenses();\n        }\n\n        // ---------- 7. SETTINGS ----------\n        async function loadSettings() {\n            const res = await fetch(\'/api/settings\');\n            const s = await res.json();\n            if(s.shop_name) {\n                document.getElementById(\'header-shop-name\').innerText = s.shop_name;\n                document.getElementById(\'set-shop-name\').value = s.shop_name || \'\';\n                document.getElementById(\'set-owner-name\').value = s.owner_name || \'\';\n                document.getElementById(\'set-mobile\').value = s.mobile || \'\';\n                document.getElementById(\'set-email\').value = s.email || \'\';\n                document.getElementById(\'set-address\').value = s.address || \'\';\n                document.getElementById(\'set-gstin\').value = s.gstin || \'\';\n                document.getElementById(\'set-upi\').value = s.upi_id || \'\';\n                document.getElementById(\'set-bank-name\').value = s.bank_name || \'\';\n                document.getElementById(\'set-bank-holder\').value = s.bank_holder || \'\';\n                document.getElementById(\'set-bank-account\').value = s.bank_account || \'\';\n                document.getElementById(\'set-bank-ifsc\').value = s.bank_ifsc || \'\';\n                document.getElementById(\'set-terms\').value = s.invoice_terms || \'\';\n                document.getElementById(\'set-footer\').value = s.invoice_footer || \'\';\n            }\n        }\n\n        async function saveSettings() {\n            const data = {\n                shop_name: document.getElementById(\'set-shop-name\').value.trim(),\n                owner_name: document.getElementById(\'set-owner-name\').value.trim(),\n                mobile: document.getElementById(\'set-mobile\').value.trim(),\n                email: document.getElementById(\'set-email\').value.trim(),\n                address: document.getElementById(\'set-address\').value.trim(),\n                gstin: document.getElementById(\'set-gstin\').value.trim(),\n                upi_id: document.getElementById(\'set-upi\').value.trim(),\n                bank_name: document.getElementById(\'set-bank-name\').value.trim(),\n                bank_holder: document.getElementById(\'set-bank-holder\').value.trim(),\n                bank_account: document.getElementById(\'set-bank-account\').value.trim(),\n                bank_ifsc: document.getElementById(\'set-bank-ifsc\').value.trim(),\n                invoice_terms: document.getElementById(\'set-terms\').value.trim(),\n                invoice_footer: document.getElementById(\'set-footer\').value.trim()\n            };\n            await fetch(\'/api/settings\', {\n                method: \'POST\',\n                headers: {\'Content-Type\': \'application/json\'},\n                body: JSON.stringify(data)\n            });\n            document.getElementById(\'header-shop-name\').innerText = data.shop_name || \'My Mobile Shop\';\n            alert("Settings saved to Cloud!");\n        }\n\n        // Initialize on load\n        loadSettings();\n        loadDashboard();\n    </script>\n</body>\n</html>\n'
EMBEDDED_INVOICE_HTML = '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Tax Invoice - {{ sale.invoice_no }}</title>\n    <script src="https://cdn.tailwindcss.com"></script>\n    <style>\n        @media print {\n            .no-print { display: none !important; }\n            body { background: white !important; padding: 0 !important; }\n            .invoice-card { box-shadow: none !important; border: none !important; }\n        }\n    </style>\n</head>\n<body class="bg-slate-100 p-4 sm:p-8 text-slate-800 font-sans">\n\n    <div class="max-w-3xl mx-auto space-y-4">\n        <!-- Print & WhatsApp Share Bar -->\n        <div class="no-print flex justify-between items-center bg-white p-3 rounded-xl border border-slate-200 shadow-sm">\n            <a href="/" class="text-xs font-bold text-slate-500 hover:text-slate-800">← Back to Dashboard</a>\n            <div class="space-x-2">\n                <button onclick="window.print()" class="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-4 py-2 rounded-lg shadow">🖨 Print / Save PDF</button>\n                <button onclick="shareWhatsApp()" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-4 py-2 rounded-lg shadow">📱 Send WhatsApp</button>\n            </div>\n        </div>\n\n        <!-- Invoice Paper Card -->\n        <div class="invoice-card bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-lg space-y-6">\n            <div class="flex justify-between items-start border-b-2 border-blue-600 pb-4">\n                <div>\n                    <h1 class="text-2xl font-black text-blue-600">{{ settings.shop_name or \'My Mobile Shop\' }}</h1>\n                    <p class="text-xs text-slate-500 mt-1 max-w-sm">{{ settings.address or \'Mobile Sales & Services\' }}</p>\n                    <p class="text-xs text-slate-500 mt-0.5">Phone: <b>{{ settings.mobile or \'\' }}</b> | Email: {{ settings.email or \'\' }}</p>\n                    {% if settings.gstin %}\n                    <p class="text-xs font-bold text-slate-700 mt-0.5">GSTIN: {{ settings.gstin }}</p>\n                    {% endif %}\n                </div>\n                <div class="text-right">\n                    <div class="inline-block bg-blue-50 text-blue-700 border border-blue-200 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider mb-1">\n                        {{ copy_type }} COPY\n                    </div>\n                    <h2 class="text-xl font-bold text-slate-900">TAX INVOICE</h2>\n                    <p class="text-xs text-slate-500 mt-1">Invoice: <b>{{ sale.invoice_no }}</b></p>\n                    <p class="text-xs text-slate-500">Date: {{ sale.created_at }}</p>\n                </div>\n            </div>\n\n            <!-- Customer & Sale Info -->\n            <div class="bg-slate-50 p-4 rounded-xl border border-slate-100 flex justify-between items-center text-xs">\n                <div>\n                    <span class="text-slate-400 font-bold block">BILLED TO:</span>\n                    <span class="text-sm font-bold text-slate-900">{{ sale.customer_name or \'Walk-in Customer\' }}</span>\n                </div>\n                <div class="text-right">\n                    <span class="text-slate-400 font-bold block">BILL TYPE:</span>\n                    <span class="text-sm font-bold text-slate-900">{{ sale.sale_type or \'GST\' }}</span>\n                </div>\n            </div>\n\n            <!-- Items Table -->\n            <table class="w-full text-left text-xs border-collapse">\n                <thead>\n                    <tr class="bg-slate-100 text-slate-700 font-bold">\n                        <th class="p-2.5 rounded-l-lg">#</th>\n                        <th class="p-2.5">Product Description</th>\n                        <th class="p-2.5 text-center">Qty</th>\n                        <th class="p-2.5 text-right">Rate</th>\n                        <th class="p-2.5 text-center">GST</th>\n                        <th class="p-2.5 text-right">Taxable</th>\n                        <th class="p-2.5 text-right rounded-r-lg">Total</th>\n                    </tr>\n                </thead>\n                <tbody class="divide-y divide-slate-100">\n                    {% for it in items %}\n                    <tr>\n                        <td class="p-2.5 text-slate-400">{{ loop.index }}</td>\n                        <td class="p-2.5 font-bold text-slate-800">\n                            {{ it.product_name }}\n                            {% if it.imei %}\n                            <br><span class="text-[10px] text-slate-400 font-normal">IMEI: {{ it.imei }}</span>\n                            {% endif %}\n                        </td>\n                        <td class="p-2.5 text-center">{{ it.qty }}</td>\n                        <td class="p-2.5 text-right">₹ {{ "%.2f"|format(it.rate) }}</td>\n                        <td class="p-2.5 text-center">{{ it.gst }}%</td>\n                        <td class="p-2.5 text-right">₹ {{ "%.2f"|format(it.taxable) }}</td>\n                        <td class="p-2.5 text-right font-bold text-slate-900">₹ {{ "%.2f"|format(it.amount) }}</td>\n                    </tr>\n                    {% endfor %}\n                </tbody>\n            </table>\n\n            <!-- Grand Totals Breakdown -->\n            <div class="flex justify-between items-start pt-3 border-t border-slate-200">\n                <div class="text-xs space-y-1">\n                    <span class="font-bold text-slate-600 block">Payment Details:</span>\n                    <p class="text-slate-500">\n                        {% if sale.cash > 0 %}Cash: ₹ {{ "%.2f"|format(sale.cash) }} | {% endif %}\n                        {% if sale.upi > 0 %}UPI: ₹ {{ "%.2f"|format(sale.upi) }} | {% endif %}\n                        {% if sale.bank > 0 %}Bank: ₹ {{ "%.2f"|format(sale.bank) }} | {% endif %}\n                        {% if sale.card > 0 %}Card: ₹ {{ "%.2f"|format(sale.card) }} | {% endif %}\n                        {% if sale.udhar > 0 %}Udhar: ₹ {{ "%.2f"|format(sale.udhar) }}{% endif %}\n                    </p>\n                    {% if settings.bank_name or settings.upi_id %}\n                    <div class="bg-blue-50 p-2.5 rounded-lg text-[11px] text-slate-700 mt-2 border border-blue-100">\n                        <b>Bank:</b> {{ settings.bank_name }} | <b>A/c:</b> {{ settings.bank_account }} | <b>IFSC:</b> {{ settings.bank_ifsc }}<br>\n                        <b>UPI ID:</b> {{ settings.upi_id }}\n                    </div>\n                    {% endif %}\n                </div>\n                <div class="w-56 space-y-1 text-right text-xs">\n                    <div class="flex justify-between text-slate-500">\n                        <span>Subtotal:</span>\n                        <span>₹ {{ "%.2f"|format(sale.subtotal) }}</span>\n                    </div>\n                    <div class="flex justify-between text-slate-500">\n                        <span>GST Total:</span>\n                        <span>₹ {{ "%.2f"|format(sale.gst_amount) }}</span>\n                    </div>\n                    <div class="flex justify-between text-base font-black text-blue-600 pt-1 border-t border-slate-200">\n                        <span>Grand Total:</span>\n                        <span>₹ {{ "%.2f"|format(sale.grand_total) }}</span>\n                    </div>\n                </div>\n            </div>\n\n            {% if settings.invoice_terms %}\n            <div class="text-[10px] text-slate-400 border-t border-slate-100 pt-3 leading-relaxed">\n                <b>Terms & Conditions:</b><br>\n                {{ settings.invoice_terms.replace(\'\\n\', \'<br>\')|safe }}\n            </div>\n            {% endif %}\n\n            <div class="flex justify-between items-end text-xs text-slate-400 pt-4 border-t border-slate-200">\n                <div>{{ settings.invoice_footer or \'Thank you for your business! Please visit again.\' }}</div>\n                <div class="text-right">\n                    Authorized Signatory<br><br>\n                    <b class="text-slate-800">{{ settings.shop_name or \'Mobile Shop\' }}</b>\n                </div>\n            </div>\n        </div>\n    </div>\n\n    <script>\n        function shareWhatsApp() {\n            const msg = `Hello {{ sale.customer_name or \'Customer\' }},\\nThank you for shopping at *{{ settings.shop_name or \'Mobile Shop\' }}*!\\n\\n📄 *Invoice No:* {{ sale.invoice_no }}\\n💰 *Total Amount:* ₹{{ "%.2f"|format(sale.grand_total) }}\\n\\nView and Download your Tax Invoice here:\\n${window.location.href}`;\n            window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(msg)}`, \'_blank\');\n        }\n    </script>\n</body>\n</html>\n'

@app.route('/')
def index():
    tpl = load_template_text('index.html', EMBEDDED_INDEX_HTML)
    return render_template_string(tpl)

@app.route('/manifest.json')
def manifest():
    manifest_path = os.path.join(STATIC_DIR, 'manifest.json')
    if os.path.exists(manifest_path):
        return send_from_directory(STATIC_DIR, 'manifest.json')
    return jsonify({
        "name": "Mobile Shop Manager",
        "short_name": "MobileShop",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0F172A",
        "theme_color": "#0F172A"
    })

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

    db = get_db()

    if from_d and to_d:
        db.execute("SELECT COALESCE(SUM(grand_total), 0) AS total, COALESCE(SUM(gst_amount), 0) AS gst, COALESCE(SUM(udhar), 0) AS udhar, COUNT(*) AS count FROM sales WHERE created_at >= %s AND created_at <= %s", (f"{from_d} 00:00:00", f"{to_d} 23:59:59"))
        sales_stat = db.fetchone()
        
        db.execute("SELECT COALESCE(SUM(final_amount), 0) AS total, COUNT(*) AS count FROM repairs WHERE received_date >= %s AND received_date <= %s", (from_d, to_d))
        repairs_stat = db.fetchone()

        db.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE created_at >= %s AND created_at <= %s", (f"{from_d} 00:00:00", f"{to_d} 23:59:59"))
        expenses_stat = db.fetchone()
    else:
        db.execute("SELECT COALESCE(SUM(grand_total), 0) AS total, COALESCE(SUM(gst_amount), 0) AS gst, COALESCE(SUM(udhar), 0) AS udhar, COUNT(*) AS count FROM sales")
        sales_stat = db.fetchone()

        db.execute("SELECT COALESCE(SUM(final_amount), 0) AS total, COUNT(*) AS count FROM repairs")
        repairs_stat = db.fetchone()

        db.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM expenses")
        expenses_stat = db.fetchone()

    db.execute("SELECT COALESCE(SUM(stock), 0) AS total_stock, COUNT(*) AS total_models FROM products")
    stock_stat = db.fetchone()

    db.execute("SELECT COUNT(*) AS count FROM customers")
    cust_count = db.fetchone()['count']

    db.execute("SELECT COUNT(*) AS pending FROM repairs WHERE status NOT IN ('Delivered', 'Cancelled')")
    pending_repairs = db.fetchone()['pending']

    # Recent Sales
    db.execute("SELECT id, invoice_no, customer_name, grand_total, created_at, sale_type FROM sales ORDER BY id DESC LIMIT 6")
    recent_sales = db.fetchall()

    # Recent Repairs
    db.execute("SELECT id, repair_no, customer, phone_model, problem, final_amount, status, received_date FROM repairs ORDER BY id DESC LIMIT 6")
    recent_repairs = db.fetchall()

    db.close()

    return jsonify({
        "sales_total": float(sales_stat['total'] or 0),
        "sales_count": int(sales_stat['count'] or 0),
        "gst_total": float(sales_stat['gst'] or 0),
        "udhar_total": float(sales_stat['udhar'] or 0),
        "repairs_total": float(repairs_stat['total'] or 0),
        "repairs_count": int(repairs_stat['count'] or 0),
        "expenses_total": float(expenses_stat['total'] or 0),
        "total_stock": int(stock_stat['total_stock'] or 0),
        "total_models": int(stock_stat['total_models'] or 0),
        "customer_count": int(cust_count or 0),
        "pending_repairs": int(pending_repairs or 0),
        "recent_sales": recent_sales,
        "recent_repairs": recent_repairs
    })

# ----------------- PRODUCTS API -----------------
@app.route('/api/products', methods=['GET', 'POST'])
def api_products():
    db = get_db()
    if request.method == 'GET':
        q = request.args.get('q', '').strip()
        if q:
            db.execute("""SELECT * FROM products WHERE brand ILIKE %s OR model ILIKE %s OR imei1 ILIKE %s OR imei2 ILIKE %s OR serial_no ILIKE %s ORDER BY id DESC""",
                       (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"))
        else:
            db.execute("SELECT * FROM products ORDER BY id DESC")
        items = db.fetchall()
        db.close()
        return jsonify(items)
    
    data = request.json
    try:
        db.execute("""INSERT INTO products(brand, model, imei1, imei2, serial_no, ram, storage, color, purchase_price, sale_price, gst, stock, supplier, created_at)
                      VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                   (data.get('brand'), data.get('model'), data.get('imei1'), data.get('imei2'), data.get('serial_no'),
                    data.get('ram'), data.get('storage'), data.get('color'), float(data.get('purchase_price') or 0),
                    float(data.get('sale_price') or 0), float(data.get('gst') or 0), int(data.get('stock') or 1),
                    data.get('supplier'), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        new_id = db.fetchone()['id']
        db.commit()
        db.close()
        return jsonify({"success": True, "id": new_id})
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400

@app.route('/api/products/<int:pid>', methods=['PUT', 'DELETE'])
def api_product_detail(pid):
    db = get_db()
    if request.method == 'DELETE':
        db.execute("DELETE FROM products WHERE id=%s", (pid,))
        db.commit()
        db.close()
        return jsonify({"success": True})
    
    data = request.json
    try:
        db.execute("""UPDATE products SET brand=%s, model=%s, imei1=%s, imei2=%s, serial_no=%s, ram=%s, storage=%s, color=%s,
                      purchase_price=%s, sale_price=%s, gst=%s, stock=%s, supplier=%s WHERE id=%s""",
                   (data.get('brand'), data.get('model'), data.get('imei1'), data.get('imei2'), data.get('serial_no'),
                    data.get('ram'), data.get('storage'), data.get('color'), float(data.get('purchase_price') or 0),
                    float(data.get('sale_price') or 0), float(data.get('gst') or 0), int(data.get('stock') or 0),
                    data.get('supplier'), pid))
        db.commit()
        db.close()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400

# ----------------- CUSTOMERS API -----------------
@app.route('/api/customers', methods=['GET', 'POST'])
def api_customers():
    db = get_db()
    if request.method == 'GET':
        q = request.args.get('q', '').strip()
        if q:
            db.execute("SELECT * FROM customers WHERE name ILIKE %s OR mobile ILIKE %s ORDER BY name ASC", (f"%{q}%", f"%{q}%"))
        else:
            db.execute("SELECT * FROM customers ORDER BY opening_balance DESC, name ASC")
        items = db.fetchall()
        db.close()
        return jsonify(items)

    data = request.json
    try:
        db.execute("""INSERT INTO customers(name, mobile, address, gstin, opening_balance, notes, created_at)
                      VALUES(%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                   (data.get('name'), data.get('mobile'), data.get('address'), data.get('gstin'),
                    float(data.get('opening_balance') or 0), data.get('notes'), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        new_id = db.fetchone()['id']
        db.commit()
        db.close()
        return jsonify({"success": True, "id": new_id})
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400

@app.route('/api/customers/<int:cid>', methods=['PUT', 'DELETE'])
def api_customer_detail(cid):
    db = get_db()
    if request.method == 'DELETE':
        db.execute("DELETE FROM customers WHERE id=%s", (cid,))
        db.commit()
        db.close()
        return jsonify({"success": True})

    data = request.json
    try:
        db.execute("""UPDATE customers SET name=%s, mobile=%s, address=%s, gstin=%s, opening_balance=%s, notes=%s WHERE id=%s""",
                   (data.get('name'), data.get('mobile'), data.get('address'), data.get('gstin'),
                    float(data.get('opening_balance') or 0), data.get('notes'), cid))
        db.commit()
        db.close()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400

# ----------------- SALES & INVOICE API -----------------
@app.route('/api/sales', methods=['GET', 'POST'])
def api_sales():
    db = get_db()
    if request.method == 'GET':
        q = request.args.get('q', '').strip()
        if q:
            db.execute("SELECT * FROM sales WHERE invoice_no ILIKE %s OR customer_name ILIKE %s ORDER BY id DESC", (f"%{q}%", f"%{q}%"))
        else:
            db.execute("SELECT * FROM sales ORDER BY id DESC LIMIT 100")
        items = db.fetchall()
        db.close()
        return jsonify(items)

    data = request.json
    items = data.get('items', [])
    if not items:
        db.close()
        return jsonify({"error": "Cart is empty"}), 400

    # Auto generate Invoice Number for current year
    year = datetime.now().year
    prefix = f"INV-{year}-"
    db.execute("SELECT invoice_no FROM sales WHERE invoice_no LIKE %s ORDER BY id DESC LIMIT 1", (f"{prefix}%",))
    last_inv = db.fetchone()
    if last_inv and last_inv.get('invoice_no'):
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
        db.execute("""INSERT INTO sales(invoice_no, customer_id, customer_name, sale_type, subtotal, gst_amount, grand_total, cash, upi, bank, card, udhar, created_at)
                      VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                   (invoice_no, cust_id, cust_name, sale_type, subtotal, gst_amt, grand_total, cash, upi, bank, card, udhar, created_at))
        sale_id = db.fetchone()['id']

        for it in items:
            db.execute("""INSERT INTO sale_items(sale_id, product_id, product_name, imei, qty, rate, gst, taxable, gst_amount, amount)
                          VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                       (sale_id, it.get('pid'), it.get('name'), it.get('imei'), it.get('qty', 1), it.get('rate', 0), it.get('gst', 0),
                        it.get('taxable', 0), it.get('gstamt', 0), it.get('amount', 0)))
            if it.get('pid'):
                db.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (it.get('qty', 1), it.get('pid')))

        if cust_id and udhar > 0:
            db.execute("UPDATE customers SET opening_balance = opening_balance + %s WHERE id = %s", (udhar, cust_id))

        db.commit()
        db.close()
        return jsonify({"success": True, "invoice_no": invoice_no, "id": sale_id})
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400

@app.route('/api/sales/<int:sid>', methods=['DELETE'])
def api_cancel_sale(sid):
    db = get_db()
    try:
        db.execute("SELECT product_id, qty FROM sale_items WHERE sale_id=%s", (sid,))
        for it in db.fetchall():
            if it.get('product_id'):
                db.execute("UPDATE products SET stock = stock + %s WHERE id=%s", (it['qty'], it['product_id']))
        db.execute("DELETE FROM sale_items WHERE sale_id=%s", (sid,))
        db.execute("DELETE FROM sales WHERE id=%s", (sid,))
        db.commit()
        db.close()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400

# ----------------- REPAIRS API -----------------
@app.route('/api/repairs', methods=['GET', 'POST'])
def api_repairs():
    db = get_db()
    if request.method == 'GET':
        q = request.args.get('q', '').strip()
        if q:
            db.execute("SELECT * FROM repairs WHERE repair_no ILIKE %s OR customer ILIKE %s OR phone_model ILIKE %s OR mobile ILIKE %s ORDER BY id DESC",
                       (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"))
        else:
            db.execute("SELECT * FROM repairs ORDER BY id DESC")
        items = db.fetchall()
        db.close()
        return jsonify(items)

    data = request.json
    year = datetime.now().year
    prefix = f"REP-{year}-"
    db.execute("SELECT repair_no FROM repairs WHERE repair_no LIKE %s ORDER BY id DESC LIMIT 1", (f"{prefix}%",))
    last_r = db.fetchone()
    if last_r and last_r.get('repair_no'):
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
        db.execute("""INSERT INTO repairs(repair_no, customer, mobile, phone_model, imei, problem, estimate, final_amount, advance, pending, status, technician, received_date, expected_date, notes)
                      VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                   (repair_no, data.get('customer'), data.get('mobile'), data.get('phone_model'), data.get('imei'),
                    data.get('problem'), float(data.get('estimate') or 0), final_amt, advance, pending,
                    data.get('status', 'Received'), data.get('technician'), datetime.now().strftime("%Y-%m-%d"),
                    data.get('expected_date'), data.get('notes')))
        new_id = db.fetchone()['id']
        db.commit()
        db.close()
        return jsonify({"success": True, "repair_no": repair_no, "id": new_id})
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400

@app.route('/api/repairs/<int:rid>', methods=['PUT', 'DELETE'])
def api_repair_detail(rid):
    db = get_db()
    if request.method == 'DELETE':
        db.execute("DELETE FROM repairs WHERE id=%s", (rid,))
        db.commit()
        db.close()
        return jsonify({"success": True})

    data = request.json
    final_amt = float(data.get('final_amount') or 0)
    advance = float(data.get('advance') or 0)
    pending = max(0, final_amt - advance)
    try:
        db.execute("""UPDATE repairs SET customer=%s, mobile=%s, phone_model=%s, imei=%s, problem=%s, estimate=%s,
                      final_amount=%s, advance=%s, pending=%s, status=%s, technician=%s, expected_date=%s, notes=%s WHERE id=%s""",
                   (data.get('customer'), data.get('mobile'), data.get('phone_model'), data.get('imei'),
                    data.get('problem'), float(data.get('estimate') or 0), final_amt, advance, pending,
                    data.get('status'), data.get('technician'), data.get('expected_date'), data.get('notes'), rid))
        db.commit()
        db.close()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400

# ----------------- EXPENSES API -----------------
@app.route('/api/expenses', methods=['GET', 'POST'])
def api_expenses():
    db = get_db()
    if request.method == 'GET':
        db.execute("SELECT * FROM expenses ORDER BY id DESC LIMIT 100")
        items = db.fetchall()
        db.close()
        return jsonify(items)

    data = request.json
    try:
        db.execute("""INSERT INTO expenses(category, description, amount, payment_mode, created_at)
                      VALUES(%s, %s, %s, %s, %s) RETURNING id""",
                   (data.get('category'), data.get('description'), float(data.get('amount') or 0),
                    data.get('payment_mode', 'Cash'), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        new_id = db.fetchone()['id']
        db.commit()
        db.close()
        return jsonify({"success": True, "id": new_id})
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400

@app.route('/api/expenses/<int:eid>', methods=['DELETE'])
def api_delete_expense(eid):
    db = get_db()
    db.execute("DELETE FROM expenses WHERE id=%s", (eid,))
    db.commit()
    db.close()
    return jsonify({"success": True})

# ----------------- SETTINGS API -----------------
@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    db = get_db()
    if request.method == 'GET':
        db.execute("SELECT * FROM settings WHERE id=1")
        item = db.fetchone()
        db.close()
        return jsonify(item or {})

    data = request.json
    try:
        db.execute("""UPDATE settings SET shop_name=%s, owner_name=%s, mobile=%s, email=%s, address=%s, gstin=%s,
                      bank_name=%s, bank_account=%s, bank_ifsc=%s, bank_holder=%s, upi_id=%s, invoice_terms=%s, invoice_footer=%s WHERE id=1""",
                   (data.get('shop_name'), data.get('owner_name'), data.get('mobile'), data.get('email'),
                    data.get('address'), data.get('gstin'), data.get('bank_name'), data.get('bank_account'),
                    data.get('bank_ifsc'), data.get('bank_holder'), data.get('upi_id'),
                    data.get('invoice_terms'), data.get('invoice_footer')))
        db.commit()
        db.close()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400

# ----------------- VIEW / PRINT INVOICE -----------------
@app.route('/invoice/<invoice_no>')
def view_invoice(invoice_no):
    copy_type = request.args.get('copy', 'ORIGINAL').upper()
    db = get_db()
    db.execute("SELECT * FROM settings WHERE id=1")
    settings = db.fetchone() or {}

    db.execute("SELECT * FROM sales WHERE invoice_no=%s", (invoice_no,))
    sale = db.fetchone()
    if not sale:
        db.close()
        return "Invoice not found", 404

    db.execute("SELECT * FROM sale_items WHERE sale_id=%s", (sale['id'],))
    items = db.fetchall()
    db.close()

    tpl = load_template_text('invoice.html', EMBEDDED_INVOICE_HTML)
    return render_template_string(tpl, settings=settings, sale=sale, items=items, copy_type=copy_type)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

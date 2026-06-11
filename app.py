"""
АИС учёта электронно-цифровых подписей сотрудников
Западного филиала РАНХиГС.

Демонстрационная версия. PostgreSQL заменён на SQLite для упрощения запуска.
SQL-схема в Приложении 1 диплома идентична по структуре.
"""

import os
import sqlite3
import csv
import io
from datetime import date, datetime, timedelta
from functools import wraps
from contextlib import closing

from flask import (
    Flask, request, redirect, url_for, render_template,
    flash, session, abort, g, Response, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'ecp_registry.db')

app = Flask(__name__)
# В продакшене берём ключ из переменной окружения (Render сам его создаёт)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'demo-secret-key-change-in-production')
app.config['DATABASE'] = DB_PATH


# Автоинициализация БД при первом запуске (если её нет)
def _ensure_db():
    if not os.path.exists(DB_PATH):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        import subprocess
        init_script = os.path.join(BASE_DIR, 'init_db.py')
        if os.path.exists(init_script):
            subprocess.run(['python', init_script], cwd=BASE_DIR, check=False)


_ensure_db()


# ============================================================
# Работа с БД
# ============================================================

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ============================================================
# Авторизация
# ============================================================

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    db = get_db()
    user = db.execute(
        'SELECT u.*, e.last_name, e.first_name, e.middle_name '
        'FROM users u LEFT JOIN employees e ON u.employee_id = e.id '
        'WHERE u.id = ? AND u.is_active = 1',
        (user_id,)
    ).fetchone()
    return user


@app.context_processor
def inject_user():
    user = get_current_user()
    if user:
        full_name = user['last_name'] or user['username']
        if user['first_name']:
            full_name += f" {user['first_name'][0]}."
        if user['middle_name']:
            full_name += f" {user['middle_name'][0]}."
    else:
        full_name = None
    
    role_display = {
        'admin': 'Администратор',
        'hr_specialist': 'Кадровая служба',
        'employee': 'Сотрудник',
    }
    
    return {
        'current_user': user,
        'current_user_name': full_name,
        'current_user_role': role_display.get(user['role']) if user else None,
        'current_year': datetime.now().year,
    }


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return redirect(url_for('login'))
            if user['role'] not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


hr_or_admin = role_required('admin', 'hr_specialist')
admin_only = role_required('admin')


# ============================================================
# Хелперы
# ============================================================

SIGNATURE_TYPES = {
    'SES': 'Простая ЭП',
    'NES': 'Усиленная неквалифицированная',
    'QES': 'Усиленная квалифицированная',
}

CERT_STATUSES = {
    'active': 'Действует',
    'expired': 'Истёк',
    'revoked': 'Отозван',
    'suspended': 'Приостановлен',
}

TOKEN_TYPES = ['Rutoken', 'JaCarta', 'eToken', 'other']
TOKEN_STATUSES = {
    'in_storage': 'На хранении',
    'issued': 'Выдан',
    'damaged': 'Повреждён',
    'decommissioned': 'Списан',
}

app.jinja_env.globals.update(
    SIGNATURE_TYPES=SIGNATURE_TYPES,
    CERT_STATUSES=CERT_STATUSES,
    TOKEN_TYPES=TOKEN_TYPES,
    TOKEN_STATUSES=TOKEN_STATUSES,
)


def log_audit(action, entity_type, entity_id, details=None):
    user = get_current_user()
    db = get_db()
    db.execute(
        'INSERT INTO audit_log (user_id, action, entity_type, entity_id, '
        'details, ip_address) VALUES (?, ?, ?, ?, ?, ?)',
        (
            user['id'] if user else None,
            action, entity_type, entity_id,
            details or '',
            request.remote_addr
        )
    )
    db.commit()


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except ValueError:
        return None


# Регистрируем функции для шаблонов
@app.template_filter('rudate')
def format_ru_date(value):
    if not value:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return value
    return value.strftime('%d.%m.%Y')


@app.template_filter('days_left')
def days_left(value):
    if not value:
        return None
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return None
    return (value - date.today()).days


# ============================================================
# Маршруты: главная и авторизация
# ============================================================

@app.route('/')
def index():
    if get_current_user():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if get_current_user():
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ? AND is_active = 1',
            (username,)
        ).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            db.execute(
                'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (user['id'],)
            )
            db.commit()
            log_audit('login', 'user', user['id'])
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        
        flash('Неверный логин или пароль', 'danger')
    
    return render_template('auth/login.html')


@app.route('/logout')
def logout():
    user = get_current_user()
    if user:
        log_audit('logout', 'user', user['id'])
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))


# ============================================================
# Дашборд
# ============================================================

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    user = get_current_user()
    today = date.today().isoformat()
    in_30 = (date.today() + timedelta(days=30)).isoformat()
    
    if user['role'] in ('admin', 'hr_specialist'):
        active_certs = db.execute(
            "SELECT COUNT(*) FROM certificates WHERE status = 'active'"
        ).fetchone()[0]
        active_poa = db.execute(
            "SELECT COUNT(*) FROM powers_of_attorney WHERE status = 'active'"
        ).fetchone()[0]
        issued_tokens = db.execute(
            "SELECT COUNT(*) FROM tokens WHERE status = 'issued'"
        ).fetchone()[0]
        total_employees = db.execute(
            "SELECT COUNT(*) FROM employees WHERE is_active = 1"
        ).fetchone()[0]
        
        expiring = db.execute(
            "SELECT c.*, e.last_name, e.first_name, e.middle_name, e.position "
            "FROM certificates c JOIN employees e ON c.owner_id = e.id "
            "WHERE c.status = 'active' AND c.valid_until BETWEEN ? AND ? "
            "ORDER BY c.valid_until LIMIT 10",
            (today, in_30)
        ).fetchall()
        
        recent_audit = db.execute(
            "SELECT a.*, u.username FROM audit_log a "
            "LEFT JOIN users u ON a.user_id = u.id "
            "ORDER BY a.timestamp DESC LIMIT 8"
        ).fetchall() if user['role'] == 'admin' else []
    else:
        # Для роли employee показываем только свои данные
        emp_id = user['employee_id']
        active_certs = db.execute(
            "SELECT COUNT(*) FROM certificates WHERE owner_id = ? AND status = 'active'",
            (emp_id,)
        ).fetchone()[0]
        active_poa = db.execute(
            "SELECT COUNT(*) FROM powers_of_attorney WHERE representative_id = ? AND status = 'active'",
            (emp_id,)
        ).fetchone()[0]
        issued_tokens = db.execute(
            "SELECT COUNT(*) FROM tokens WHERE current_holder_id = ?",
            (emp_id,)
        ).fetchone()[0]
        total_employees = 1
        
        expiring = db.execute(
            "SELECT c.*, e.last_name, e.first_name, e.middle_name, e.position "
            "FROM certificates c JOIN employees e ON c.owner_id = e.id "
            "WHERE c.owner_id = ? AND c.status = 'active' "
            "AND c.valid_until BETWEEN ? AND ? "
            "ORDER BY c.valid_until",
            (emp_id, today, in_30)
        ).fetchall()
        recent_audit = []
    
    return render_template(
        'dashboard/index.html',
        active_certs=active_certs,
        active_poa=active_poa,
        issued_tokens=issued_tokens,
        total_employees=total_employees,
        expiring=expiring,
        recent_audit=recent_audit,
    )


# ============================================================
# Сертификаты
# ============================================================

@app.route('/certificates')
@login_required
def certificates_list():
    db = get_db()
    user = get_current_user()
    
    search = request.args.get('q', '').strip()
    sig_type = request.args.get('type', '')
    status = request.args.get('status', '')
    page = int(request.args.get('page', 1))
    per_page = 25
    
    where = []
    params = []
    
    if user['role'] == 'employee':
        where.append('c.owner_id = ?')
        params.append(user['employee_id'])
    
    if search:
        where.append('(c.serial_number LIKE ? OR e.last_name LIKE ?)')
        params.extend([f'%{search}%', f'%{search}%'])
    if sig_type in SIGNATURE_TYPES:
        where.append('c.signature_type = ?')
        params.append(sig_type)
    if status in CERT_STATUSES:
        where.append('c.status = ?')
        params.append(status)
    
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
    
    total = db.execute(
        f'SELECT COUNT(*) FROM certificates c '
        f'JOIN employees e ON c.owner_id = e.id {where_sql}',
        params
    ).fetchone()[0]
    
    offset = (page - 1) * per_page
    certs = db.execute(
        f'SELECT c.*, e.last_name, e.first_name, e.middle_name, e.position, '
        f'       ca.name AS ca_name, t.serial_number AS token_serial '
        f'FROM certificates c '
        f'JOIN employees e ON c.owner_id = e.id '
        f'LEFT JOIN certification_authorities ca ON c.ca_id = ca.id '
        f'LEFT JOIN tokens t ON c.token_id = t.id '
        f'{where_sql} '
        f'ORDER BY c.valid_until DESC '
        f'LIMIT ? OFFSET ?',
        params + [per_page, offset]
    ).fetchall()
    
    total_pages = (total + per_page - 1) // per_page
    
    return render_template(
        'certificates/list.html',
        certs=certs, total=total, page=page, total_pages=total_pages,
        search=search, sig_type=sig_type, status=status,
    )


@app.route('/certificates/<int:cert_id>')
@login_required
def certificate_detail(cert_id):
    db = get_db()
    user = get_current_user()
    
    cert = db.execute(
        'SELECT c.*, e.last_name, e.first_name, e.middle_name, e.position, '
        '       e.department_id, d.name AS department_name, '
        '       ca.name AS ca_name, t.serial_number AS token_serial '
        'FROM certificates c '
        'JOIN employees e ON c.owner_id = e.id '
        'LEFT JOIN departments d ON e.department_id = d.id '
        'LEFT JOIN certification_authorities ca ON c.ca_id = ca.id '
        'LEFT JOIN tokens t ON c.token_id = t.id '
        'WHERE c.id = ?',
        (cert_id,)
    ).fetchone()
    
    if not cert:
        abort(404)
    
    if user['role'] == 'employee' and cert['owner_id'] != user['employee_id']:
        abort(403)
    
    # Связанные МЧД
    related_poa = db.execute(
        'SELECT poa.*, e.last_name, e.first_name '
        'FROM powers_of_attorney poa '
        'JOIN employees e ON poa.representative_id = e.id '
        'WHERE poa.principal_certificate_id = ? OR poa.representative_certificate_id = ?',
        (cert_id, cert_id)
    ).fetchall()
    
    return render_template(
        'certificates/detail.html',
        cert=cert, related_poa=related_poa,
    )


@app.route('/certificates/new', methods=['GET', 'POST'])
@hr_or_admin
def certificate_new():
    db = get_db()
    
    if request.method == 'POST':
        serial = request.form.get('serial_number', '').strip()
        sig_type = request.form.get('signature_type')
        owner_id = request.form.get('owner_id', type=int)
        ca_id = request.form.get('ca_id', type=int) or None
        token_id = request.form.get('token_id', type=int) or None
        issued_at = parse_date(request.form.get('issued_at'))
        valid_from = parse_date(request.form.get('valid_from'))
        valid_until = parse_date(request.form.get('valid_until'))
        purpose = request.form.get('purpose', '').strip()
        
        errors = []
        if not serial: errors.append('Не указан серийный номер')
        if sig_type not in SIGNATURE_TYPES: errors.append('Не выбран тип подписи')
        if not owner_id: errors.append('Не выбран владелец')
        if not issued_at: errors.append('Не указана дата выдачи')
        if not valid_from: errors.append('Не указано начало срока действия')
        if not valid_until: errors.append('Не указано окончание срока действия')
        if valid_from and valid_until and valid_until <= valid_from:
            errors.append('Дата окончания должна быть позже даты начала')
        
        if errors:
            for e in errors: flash(e, 'danger')
        else:
            try:
                cur = db.execute(
                    'INSERT INTO certificates '
                    '(serial_number, signature_type, owner_id, ca_id, token_id, '
                    ' issued_at, valid_from, valid_until, purpose, status) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (serial, sig_type, owner_id, ca_id, token_id,
                     issued_at, valid_from, valid_until, purpose, 'active')
                )
                db.commit()
                log_audit('create', 'certificate', cur.lastrowid, serial)
                flash(f'Сертификат {serial} зарегистрирован', 'success')
                return redirect(url_for('certificate_detail', cert_id=cur.lastrowid))
            except sqlite3.IntegrityError as e:
                flash(f'Ошибка: сертификат с таким серийным номером уже существует', 'danger')
    
    employees = db.execute(
        'SELECT id, last_name, first_name, middle_name, position '
        'FROM employees WHERE is_active = 1 ORDER BY last_name'
    ).fetchall()
    cas = db.execute('SELECT id, name FROM certification_authorities ORDER BY name').fetchall()
    tokens = db.execute(
        "SELECT id, serial_number, token_type FROM tokens "
        "WHERE status IN ('in_storage', 'issued') ORDER BY token_type, serial_number"
    ).fetchall()
    
    return render_template(
        'certificates/form.html',
        mode='create', cert=None,
        employees=employees, cas=cas, tokens=tokens,
    )


@app.route('/certificates/<int:cert_id>/revoke', methods=['POST'])
@hr_or_admin
def certificate_revoke(cert_id):
    db = get_db()
    reason = request.form.get('reason', '').strip()
    
    cert = db.execute('SELECT * FROM certificates WHERE id = ?', (cert_id,)).fetchone()
    if not cert:
        abort(404)
    if cert['status'] != 'active':
        flash('Можно отозвать только действующий сертификат', 'warning')
        return redirect(url_for('certificate_detail', cert_id=cert_id))
    
    db.execute(
        "UPDATE certificates SET status = 'revoked', "
        "revocation_date = CURRENT_DATE, revocation_reason = ? "
        "WHERE id = ?",
        (reason, cert_id)
    )
    db.commit()
    log_audit('revoke', 'certificate', cert_id, f"Причина: {reason}")
    
    flash(f"Сертификат {cert['serial_number']} отозван", 'info')
    return redirect(url_for('certificate_detail', cert_id=cert_id))


# ============================================================
# МЧД
# ============================================================

@app.route('/poa')
@login_required
def poa_list():
    db = get_db()
    user = get_current_user()
    
    where = []
    params = []
    if user['role'] == 'employee':
        where.append('poa.representative_id = ?')
        params.append(user['employee_id'])
    
    status = request.args.get('status', '')
    if status in ('active', 'expired', 'revoked'):
        where.append('poa.status = ?')
        params.append(status)
    
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
    
    items = db.execute(
        f'SELECT poa.*, e.last_name, e.first_name, e.middle_name, e.position '
        f'FROM powers_of_attorney poa '
        f'JOIN employees e ON poa.representative_id = e.id '
        f'{where_sql} '
        f'ORDER BY poa.valid_until DESC',
        params
    ).fetchall()
    
    return render_template('poa/list.html', items=items, status=status)


@app.route('/poa/<int:poa_id>')
@login_required
def poa_detail(poa_id):
    db = get_db()
    user = get_current_user()
    
    poa = db.execute(
        'SELECT poa.*, e.last_name, e.first_name, e.middle_name, e.position '
        'FROM powers_of_attorney poa '
        'JOIN employees e ON poa.representative_id = e.id '
        'WHERE poa.id = ?',
        (poa_id,)
    ).fetchone()
    
    if not poa:
        abort(404)
    if user['role'] == 'employee' and poa['representative_id'] != user['employee_id']:
        abort(403)
    
    return render_template('poa/detail.html', poa=poa)


# ============================================================
# Токены
# ============================================================

@app.route('/tokens')
@login_required
def tokens_list():
    db = get_db()
    user = get_current_user()
    
    where = []
    params = []
    if user['role'] == 'employee':
        where.append('t.current_holder_id = ?')
        params.append(user['employee_id'])
    
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
    
    tokens = db.execute(
        f'SELECT t.*, e.last_name, e.first_name, e.middle_name '
        f'FROM tokens t '
        f'LEFT JOIN employees e ON t.current_holder_id = e.id '
        f'{where_sql} '
        f'ORDER BY t.token_type, t.serial_number',
        params
    ).fetchall()
    
    return render_template('tokens/list.html', tokens=tokens)


# ============================================================
# Сотрудники
# ============================================================

@app.route('/employees')
@hr_or_admin
def employees_list():
    db = get_db()
    search = request.args.get('q', '').strip()
    
    if search:
        rows = db.execute(
            "SELECT e.*, d.name AS department_name, "
            "(SELECT COUNT(*) FROM certificates c WHERE c.owner_id = e.id AND c.status = 'active') AS active_certs "
            "FROM employees e LEFT JOIN departments d ON e.department_id = d.id "
            "WHERE e.last_name LIKE ? OR e.first_name LIKE ? "
            "ORDER BY e.is_active DESC, e.last_name",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT e.*, d.name AS department_name, "
            "(SELECT COUNT(*) FROM certificates c WHERE c.owner_id = e.id AND c.status = 'active') AS active_certs "
            "FROM employees e LEFT JOIN departments d ON e.department_id = d.id "
            "ORDER BY e.is_active DESC, e.last_name"
        ).fetchall()
    
    return render_template('employees/list.html', employees=rows, search=search)


# ============================================================
# Отчёты
# ============================================================

@app.route('/reports')
@hr_or_admin
def reports_index():
    return render_template('reports/index.html')


@app.route('/reports/active-certificates')
@hr_or_admin
def report_active_certs():
    db = get_db()
    today = date.today().isoformat()
    
    rows = db.execute(
        "SELECT c.serial_number, c.signature_type, c.valid_from, c.valid_until, "
        "       e.last_name, e.first_name, e.middle_name, e.position, "
        "       d.name AS department_name, ca.name AS ca_name "
        "FROM certificates c "
        "JOIN employees e ON c.owner_id = e.id "
        "LEFT JOIN departments d ON e.department_id = d.id "
        "LEFT JOIN certification_authorities ca ON c.ca_id = ca.id "
        "WHERE c.status = 'active' AND c.valid_until >= ? "
        "ORDER BY c.valid_until",
        (today,)
    ).fetchall()
    
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')
    writer.writerow([
        '№', 'Серийный номер', 'Тип ЭП', 'Владелец', 'Должность',
        'Подразделение', 'УЦ', 'Действителен с', 'Действителен по', 'Дней до истечения'
    ])
    today_date = date.today()
    for i, r in enumerate(rows, 1):
        fio = f"{r['last_name']} {r['first_name']}"
        if r['middle_name']: fio += f" {r['middle_name']}"
        valid_until = datetime.strptime(r['valid_until'], '%Y-%m-%d').date()
        valid_from = datetime.strptime(r['valid_from'], '%Y-%m-%d').date()
        writer.writerow([
            i, r['serial_number'],
            SIGNATURE_TYPES.get(r['signature_type'], r['signature_type']),
            fio, r['position'], r['department_name'] or '',
            r['ca_name'] or '',
            valid_from.strftime('%d.%m.%Y'),
            valid_until.strftime('%d.%m.%Y'),
            (valid_until - today_date).days
        ])
    
    log_audit('export', 'report', 0, 'active_certificates')
    
    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=active_certificates.csv'}
    )


# ============================================================
# Журнал аудита
# ============================================================

@app.route('/audit')
@admin_only
def audit_log_view():
    db = get_db()
    rows = db.execute(
        "SELECT a.*, u.username FROM audit_log a "
        "LEFT JOIN users u ON a.user_id = u.id "
        "ORDER BY a.timestamp DESC LIMIT 200"
    ).fetchall()
    return render_template('admin/audit.html', rows=rows)


# ============================================================
# Обработчики ошибок
# ============================================================

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, message='Доступ запрещён'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='Страница не найдена'), 404


if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)

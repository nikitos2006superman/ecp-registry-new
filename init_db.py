"""Скрипт инициализации демонстрационной БД АИС учёта ЭЦП.

Заполняет базу реалистичным набором тестовых данных:
~70 сотрудников, ~95 сертификатов, ~60 МЧД, ~25 токенов.
"""

import os
import sqlite3
import random
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'ecp_registry.db')
SCHEMA = os.path.join(BASE_DIR, 'schema.sql')

# Удаляем старую БД
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Создаём схему
with open(SCHEMA, encoding='utf-8') as f:
    conn.executescript(f.read())

cur = conn.cursor()

# ============================================================
# Подразделения
# ============================================================
DEPARTMENTS = [
    ('Руководство', 'Руководство'),
    ('Отделение СПО «Право и организация социального обеспечения»', 'СПО Право'),
    ('Отделение СПО «Информационные системы и программирование»', 'СПО ИТ'),
    ('Отделение СПО «Экономика и бухгалтерский учёт»', 'СПО Экономика'),
    ('Кафедра государственного и муниципального управления', 'Кафедра ГМУ'),
    ('Учебно-методический отдел', 'УМО'),
    ('Бухгалтерия', 'Бухгалтерия'),
    ('Отдел кадров', 'Кадры'),
    ('Отдел по закупкам и хозяйственному обеспечению', 'Закупки'),
    ('Библиотека', 'Библиотека'),
    ('IT-служба', 'IT'),
    ('Канцелярия', 'Канцелярия'),
]
for name, short in DEPARTMENTS:
    cur.execute('INSERT INTO departments (name, short_name) VALUES (?, ?)', (name, short))


# ============================================================
# Удостоверяющие центры
# ============================================================
CAS = [
    ('УЦ ФНС России', '1047707030513', 1, '2022-01-01'),
    ('АО «Аналитический центр» (Контур.УЦ)', '1027600787126', 1, '2021-12-20'),
    ('АО «ПФ «СКБ Контур»', '1026605606620', 1, '2021-12-15'),
    ('ООО «Компания «Тензор»', '1027600787994', 1, '2021-12-22'),
    ('АО «СберКорус»', '1097746299353', 1, '2022-01-10'),
    ('ООО «КРИПТО-ПРО»', '1037700085444', 1, '2022-02-01'),
]
for name, ogrn, accred, acc_date in CAS:
    cur.execute(
        'INSERT INTO certification_authorities (name, ogrn, is_accredited, accreditation_date) VALUES (?, ?, ?, ?)',
        (name, ogrn, accred, acc_date)
    )


# ============================================================
# Сотрудники
# ============================================================
SURNAMES_M = ['Петров', 'Сидоров', 'Кузнецов', 'Смирнов', 'Морозов', 'Волков', 'Лебедев',
              'Соколов', 'Попов', 'Васильев', 'Никитин', 'Иванов', 'Михайлов', 'Новиков',
              'Фёдоров', 'Алексеев', 'Орлов', 'Романов', 'Захаров', 'Гончаров', 'Степанов',
              'Антонов', 'Карпов', 'Тимофеев', 'Тихонов', 'Беляев', 'Сергеев']
SURNAMES_F = ['Петрова', 'Сидорова', 'Кузнецова', 'Смирнова', 'Морозова', 'Волкова', 'Лебедева',
              'Соколова', 'Попова', 'Васильева', 'Никитина', 'Иванова', 'Михайлова', 'Новикова',
              'Фёдорова', 'Алексеева', 'Орлова', 'Романова', 'Захарова', 'Гончарова', 'Степанова',
              'Антонова', 'Карпова', 'Тимофеева', 'Тихонова', 'Беляева', 'Сергеева']
NAMES_M = ['Александр', 'Алексей', 'Андрей', 'Виктор', 'Владимир', 'Дмитрий', 'Игорь', 'Михаил',
           'Николай', 'Олег', 'Павел', 'Сергей', 'Артём', 'Константин', 'Илья', 'Денис']
NAMES_F = ['Анна', 'Елена', 'Ирина', 'Мария', 'Наталья', 'Ольга', 'Светлана', 'Татьяна',
           'Юлия', 'Екатерина', 'Людмила', 'Галина', 'Александра', 'Валентина', 'Надежда']
PATRONS_M = ['Александрович', 'Алексеевич', 'Андреевич', 'Викторович', 'Владимирович',
             'Дмитриевич', 'Игоревич', 'Михайлович', 'Николаевич', 'Олегович', 'Сергеевич', 'Петрович']
PATRONS_F = ['Александровна', 'Алексеевна', 'Андреевна', 'Викторовна', 'Владимировна',
             'Дмитриевна', 'Игоревна', 'Михайловна', 'Николаевна', 'Олеговна', 'Сергеевна', 'Петровна']

POSITIONS = {
    1: ['Директор филиала', 'Заместитель директора по учебной работе',
        'Заместитель директора по административно-хозяйственной работе'],
    2: ['Председатель ПЦК', 'Преподаватель', 'Преподаватель', 'Преподаватель', 'Преподаватель',
        'Преподаватель', 'Заведующий отделением'],
    3: ['Председатель ПЦК', 'Преподаватель', 'Преподаватель', 'Преподаватель', 'Преподаватель',
        'Заведующий отделением'],
    4: ['Председатель ПЦК', 'Преподаватель', 'Преподаватель', 'Преподаватель',
        'Заведующий отделением'],
    5: ['Заведующий кафедрой', 'Доцент', 'Доцент', 'Старший преподаватель',
        'Старший преподаватель', 'Преподаватель'],
    6: ['Начальник УМО', 'Методист', 'Методист', 'Специалист по учебно-методической работе'],
    7: ['Главный бухгалтер', 'Заместитель главного бухгалтера', 'Бухгалтер', 'Бухгалтер'],
    8: ['Начальник отдела кадров', 'Специалист по кадрам', 'Специалист по кадрам'],
    9: ['Начальник отдела', 'Специалист по закупкам', 'Контрактный управляющий',
        'Заведующий хозяйством', 'Уборщик служебных помещений', 'Уборщик служебных помещений'],
    10: ['Заведующий библиотекой', 'Библиотекарь', 'Библиотекарь'],
    11: ['Начальник IT-службы', 'Системный администратор', 'Инженер-программист'],
    12: ['Заведующий канцелярией', 'Делопроизводитель'],
}

random.seed(42)

employees = []
emp_id = 0
for dept_id, positions in POSITIONS.items():
    for pos in positions:
        emp_id += 1
        is_female = random.random() > 0.4
        if is_female:
            surname = random.choice(SURNAMES_F)
            name = random.choice(NAMES_F)
            patron = random.choice(PATRONS_F)
        else:
            surname = random.choice(SURNAMES_M)
            name = random.choice(NAMES_M)
            patron = random.choice(PATRONS_M)
        
        snils = f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(100, 999)} {random.randint(10, 99)}"
        inn = ''.join(str(random.randint(0, 9)) for _ in range(12))
        email_login = f"{surname.lower()}_{name[0].lower()}"
        email_login = email_login.translate(str.maketrans(
            'абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
            'abvgdeezzijklmnoprstufhcsss_y_eua'
        ))
        email = f"{email_login}@zf.ranepa.ru"
        phone = f"+7 (4012) 5{random.randint(10000, 99999)}"
        
        hired_year = random.randint(2018, 2024)
        hired_at = date(hired_year, random.randint(1, 12), random.randint(1, 28))
        is_active = 1 if random.random() > 0.08 else 0
        dismissed_at = None
        if not is_active:
            dismissed_at = hired_at + timedelta(days=random.randint(180, 1800))
        
        cur.execute(
            'INSERT INTO employees (last_name, first_name, middle_name, snils, inn, '
            'position, department_id, email, phone, is_active, hired_at, dismissed_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (surname, name, patron, snils, inn, pos, dept_id, email, phone,
             is_active, hired_at.isoformat(),
             dismissed_at.isoformat() if dismissed_at else None)
        )
        employees.append({
            'id': cur.lastrowid, 'surname': surname, 'name': name, 'patron': patron,
            'position': pos, 'dept_id': dept_id, 'is_active': is_active,
        })

print(f"Сотрудников: {len(employees)} (активных: {sum(1 for e in employees if e['is_active'])})")


# ============================================================
# Токены
# ============================================================
tokens_data = []
TOKEN_MODELS = {
    'Rutoken': ['Rutoken Lite 64 КБ', 'Rutoken ЭЦП 2.0', 'Rutoken ЭЦП 3.0'],
    'JaCarta': ['JaCarta-2 ГОСТ', 'JaCarta PKI'],
    'eToken': ['eToken 5110'],
}

# Кто должен иметь токены: те, кому нужны ЭП по работе
holders_pool = [e for e in employees if e['is_active'] and e['position'] in (
    'Директор филиала', 'Заместитель директора по учебной работе',
    'Заместитель директора по административно-хозяйственной работе',
    'Председатель ПЦК', 'Заведующий отделением', 'Заведующий кафедрой', 'Доцент',
    'Начальник УМО', 'Методист',
    'Главный бухгалтер', 'Заместитель главного бухгалтера', 'Бухгалтер',
    'Начальник отдела кадров', 'Специалист по кадрам',
    'Начальник отдела', 'Специалист по закупкам', 'Контрактный управляющий',
    'Начальник IT-службы',
)]

# Около 25 токенов
for i in range(25):
    token_type = random.choices(['Rutoken', 'JaCarta', 'eToken'], weights=[7, 3, 1])[0]
    model = random.choice(TOKEN_MODELS[token_type])
    serial = f"{random.randint(10000000, 99999999)}"
    purchase = date(random.randint(2022, 2024), random.randint(1, 12), random.randint(1, 28))
    
    if i < len(holders_pool):
        holder = holders_pool[i]
        status = 'issued'
        holder_id = holder['id']
    else:
        status = 'in_storage'
        holder_id = None
    
    cur.execute(
        'INSERT INTO tokens (serial_number, token_type, model, purchase_date, status, current_holder_id) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (serial, token_type, model, purchase.isoformat(), status, holder_id)
    )
    tokens_data.append({
        'id': cur.lastrowid, 'serial': serial,
        'holder_id': holder_id, 'status': status,
    })

print(f"Токенов: {len(tokens_data)}")


# ============================================================
# Сертификаты
# ============================================================
# Кому нужны сертификаты — те же что и токены, плюс ещё несколько преподавателей
cert_owners = list(holders_pool)
extra_teachers = [e for e in employees if e['is_active'] and
                  e['position'] in ('Преподаватель', 'Старший преподаватель') and
                  e not in cert_owners]
random.shuffle(extra_teachers)
cert_owners.extend(extra_teachers[:5])

today = date.today()
ca_ids = [r['id'] for r in cur.execute('SELECT id FROM certification_authorities').fetchall()]

cert_count = 0
for owner in cert_owners:
    # У каждого 1-3 сертификата
    n = random.choices([1, 2, 3], weights=[5, 3, 2])[0]
    
    for j in range(n):
        # Тип подписи
        if owner['position'] in ('Директор филиала', 'Главный бухгалтер'):
            sig_type = 'QES'
        elif owner['position'].startswith('Преподаватель'):
            sig_type = random.choice(['NES', 'NES', 'QES'])
        else:
            sig_type = random.choice(['QES', 'QES', 'NES'])
        
        # Срок действия. Стараемся сделать чтобы:
        # - 70% активных
        # - около 10% с истекающим сроком (в ближайшие 30 дней)
        # - около 5% уже истёкших
        # - остальные с большим запасом
        valid_from_days_ago = random.randint(30, 700)
        valid_from = today - timedelta(days=valid_from_days_ago)
        issued_at = valid_from
        
        bucket = random.random()
        if bucket < 0.05:  # Уже истекли
            valid_until = today - timedelta(days=random.randint(1, 60))
            status = 'expired'
        elif bucket < 0.12:  # Истекают в ближайшие 30 дней
            valid_until = today + timedelta(days=random.randint(1, 30))
            status = 'active'
        elif bucket < 0.92:  # Действуют ещё долго
            valid_until = today + timedelta(days=random.randint(60, 730))
            status = 'active'
        else:  # Отозванные
            valid_until = today + timedelta(days=random.randint(60, 400))
            status = 'revoked'
        
        serial = ':'.join([f'{random.randint(0, 255):02x}' for _ in range(8)])
        
        # Привязка к токену для КЭП
        token_id = None
        if sig_type == 'QES':
            owner_tokens = [t for t in tokens_data if t['holder_id'] == owner['id']]
            if owner_tokens:
                token_id = owner_tokens[0]['id']
        
        ca_id = random.choice(ca_ids)
        # Для директора и руководящих — ФНС
        if owner['position'] in ('Директор филиала',) and sig_type == 'QES':
            ca_id = 1  # УЦ ФНС
        
        purpose_map = {
            'Главный бухгалтер': 'Сдача бухгалтерской и налоговой отчётности',
            'Бухгалтер': 'Сдача отчётности в СФР',
            'Специалист по закупкам': 'Работа в ЕИС',
            'Контрактный управляющий': 'Подписание контрактов в ЕИС',
            'Директор филиала': 'Подписание документов от имени филиала',
            'Преподаватель': 'Подписание ведомостей и зачётных листов',
            'Методист': 'Работа в ФИС ФРДО',
            'Начальник отдела кадров': 'Подписание кадровых документов',
            'Специалист по кадрам': 'Подписание кадровых документов',
        }
        purpose = purpose_map.get(owner['position'], 'Подписание служебных документов')
        
        revocation_date = None
        revocation_reason = None
        if status == 'revoked':
            revocation_date = today - timedelta(days=random.randint(1, 90))
            revocation_reason = random.choice([
                'Смена должности', 'Компрометация ключа',
                'Прекращение трудовых отношений', 'Выпуск нового сертификата'
            ])
        
        try:
            cur.execute(
                'INSERT INTO certificates '
                '(serial_number, signature_type, owner_id, ca_id, token_id, '
                ' issued_at, valid_from, valid_until, status, purpose, '
                ' revocation_date, revocation_reason) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (serial, sig_type, owner['id'], ca_id, token_id,
                 issued_at.isoformat(), valid_from.isoformat(),
                 valid_until.isoformat(), status, purpose,
                 revocation_date.isoformat() if revocation_date else None,
                 revocation_reason)
            )
            cert_count += 1
        except sqlite3.IntegrityError:
            pass

print(f"Сертификатов: {cert_count}")


# ============================================================
# МЧД
# ============================================================
# Доверитель - директор (первый сотрудник). Доверенные лица — сотрудники с КЭП
director = employees[0]
director_cert = cur.execute(
    "SELECT id FROM certificates WHERE owner_id = ? AND signature_type = 'QES' "
    "AND status = 'active' ORDER BY valid_until DESC LIMIT 1",
    (director['id'],)
).fetchone()

POWERS_DESC = [
    ('Сдача отчётности в ФНС России', '1,2,3'),
    ('Сдача отчётности в Социальный фонд России', '4,5'),
    ('Подписание документов в ЕИС «Закупки»', '10,11,12'),
    ('Работа в ФИС ФРДО', '20'),
    ('Подписание актов выполненных работ', '6,7'),
    ('Подписание кадровых документов', '15,16'),
    ('Подписание учебных документов', '30,31'),
]

poa_count = 0
rep_candidates = cur.execute(
    "SELECT DISTINCT e.id, c.id as cert_id FROM employees e "
    "JOIN certificates c ON c.owner_id = e.id "
    "WHERE c.signature_type = 'QES' AND c.status = 'active' AND e.id != ?",
    (director['id'],)
).fetchall()

for i, rep in enumerate(rep_candidates[:30]):
    desc, codes = random.choice(POWERS_DESC)
    issued_at = today - timedelta(days=random.randint(30, 400))
    valid_from = issued_at
    
    bucket = random.random()
    if bucket < 0.10:
        valid_until = today + timedelta(days=random.randint(1, 30))
        status = 'active'
    elif bucket < 0.85:
        valid_until = today + timedelta(days=random.randint(60, 400))
        status = 'active'
    elif bucket < 0.95:
        valid_until = today - timedelta(days=random.randint(1, 90))
        status = 'expired'
    else:
        valid_until = today + timedelta(days=random.randint(60, 300))
        status = 'revoked'
    
    poa_number = f"МЧД-{2025 if issued_at.year == 2025 else issued_at.year}-{i+1:04d}"
    
    try:
        cur.execute(
            'INSERT INTO powers_of_attorney '
            '(poa_number, principal_certificate_id, representative_id, '
            ' representative_certificate_id, powers_description, powers_codes, '
            ' issued_at, valid_from, valid_until, status, fns_registered) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (poa_number,
             director_cert['id'] if director_cert else None,
             rep['id'], rep['cert_id'],
             desc, codes,
             issued_at.isoformat(), valid_from.isoformat(),
             valid_until.isoformat(), status,
             1 if random.random() > 0.2 else 0)
        )
        poa_count += 1
    except sqlite3.IntegrityError:
        pass

print(f"МЧД: {poa_count}")


# ============================================================
# Транзакции токенов
# ============================================================
for t in tokens_data:
    if t['status'] == 'issued' and t['holder_id']:
        tr_date = date.today() - timedelta(days=random.randint(30, 700))
        cur.execute(
            'INSERT INTO token_transactions '
            '(token_id, employee_id, transaction_type, transaction_date, act_number, operator_id) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (t['id'], t['holder_id'], 'issued',
             tr_date.isoformat(), f"АКТ-{random.randint(100, 999)}/2024",
             employees[0]['id'])
        )


# ============================================================
# Пользователи системы
# ============================================================

# Найдём специалиста по кадрам
hr_specialist = next((e for e in employees if e['position'] == 'Специалист по кадрам' and e['is_active']), None)
admin_employee = next((e for e in employees if e['position'] == 'Начальник IT-службы' and e['is_active']), None)
director_employee = employees[0]

users_data = [
    ('admin', 'admin123', admin_employee['id'] if admin_employee else None, 'admin'),
    ('kadry', 'kadry123', hr_specialist['id'] if hr_specialist else None, 'hr_specialist'),
    ('director', 'director123', director_employee['id'], 'employee'),
]

for username, password, emp_id, role in users_data:
    cur.execute(
        'INSERT INTO users (username, password_hash, employee_id, role, is_active) '
        'VALUES (?, ?, ?, ?, 1)',
        (username, generate_password_hash(password), emp_id, role)
    )

print(f"Пользователей: {len(users_data)}")


# ============================================================
# Журнал аудита (немного истории)
# ============================================================
for i in range(20):
    ts = datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
    actions = [
        ('login', 'user', 'Вход в систему'),
        ('create', 'certificate', 'Регистрация сертификата'),
        ('export', 'report', 'Выгрузка отчёта active_certificates'),
        ('revoke', 'certificate', 'Отзыв сертификата'),
        ('create', 'poa', 'Регистрация МЧД'),
        ('update', 'employee', 'Обновление сведений о сотруднике'),
    ]
    action, entity, details = random.choice(actions)
    user_id = random.choice([1, 2])
    cur.execute(
        'INSERT INTO audit_log (user_id, action, entity_type, entity_id, details, ip_address, timestamp) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (user_id, action, entity, random.randint(1, 100), details, '192.168.1.45',
         ts.isoformat(' '))
    )

conn.commit()
conn.close()

print("\nИнициализация БД завершена.")
print(f"БД: {DB_PATH}")
print("\nУчётные записи для входа:")
print("  admin    / admin123    — Администратор (полный доступ)")
print("  kadry    / kadry123    — Кадровая служба")
print("  director / director123 — Сотрудник (доступ только к своим данным)")

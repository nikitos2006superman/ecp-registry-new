-- Схема базы данных АИС учёта ЭЦП

-- Подразделения
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    short_name TEXT,
    parent_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES departments(id)
);

-- Удостоверяющие центры
CREATE TABLE IF NOT EXISTS certification_authorities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    ogrn TEXT,
    is_accredited BOOLEAN DEFAULT 0,
    accreditation_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Сотрудники
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    snils TEXT UNIQUE,
    inn TEXT UNIQUE,
    position TEXT NOT NULL,
    department_id INTEGER,
    email TEXT,
    phone TEXT,
    is_active BOOLEAN DEFAULT 1,
    hired_at DATE,
    dismissed_at DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

-- Токены (носители ключей)
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_number TEXT NOT NULL UNIQUE,
    token_type TEXT NOT NULL,
    model TEXT,
    purchase_date DATE,
    status TEXT DEFAULT 'in_storage',
    current_holder_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (current_holder_id) REFERENCES employees(id)
);

-- Сертификаты ЭП
CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_number TEXT NOT NULL UNIQUE,
    signature_type TEXT NOT NULL,
    owner_id INTEGER NOT NULL,
    ca_id INTEGER,
    token_id INTEGER,
    issued_at DATE NOT NULL,
    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,
    status TEXT DEFAULT 'active',
    purpose TEXT,
    revocation_date DATE,
    revocation_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES employees(id),
    FOREIGN KEY (ca_id) REFERENCES certification_authorities(id),
    FOREIGN KEY (token_id) REFERENCES tokens(id)
);

-- Машиночитаемые доверенности (МЧД)
CREATE TABLE IF NOT EXISTS powers_of_attorney (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poa_number TEXT NOT NULL UNIQUE,
    principal_certificate_id INTEGER,
    representative_id INTEGER NOT NULL,
    representative_certificate_id INTEGER,
    powers_description TEXT,
    powers_codes TEXT,
    issued_at DATE NOT NULL,
    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,
    status TEXT DEFAULT 'active',
    fns_registered BOOLEAN DEFAULT 0,
    xml_file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (representative_id) REFERENCES employees(id)
);

-- Транзакции токенов (выдача/возврат)
CREATE TABLE IF NOT EXISTS token_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,
    transaction_date DATE NOT NULL,
    act_number TEXT,
    operator_id INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (token_id) REFERENCES tokens(id),
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (operator_id) REFERENCES employees(id)
);

-- Пользователи системы
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    employee_id INTEGER,
    role TEXT DEFAULT 'employee',
    is_active BOOLEAN DEFAULT 1,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

-- Журнал аудита
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id INTEGER,
    details TEXT,
    ip_address TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Индексы для производительности
CREATE INDEX idx_certificates_owner ON certificates(owner_id);
CREATE INDEX idx_certificates_status ON certificates(status);
CREATE INDEX idx_certificates_valid_until ON certificates(valid_until);
CREATE INDEX idx_employees_department ON employees(department_id);
CREATE INDEX idx_employees_active ON employees(is_active);
CREATE INDEX idx_tokens_holder ON tokens(current_holder_id);
CREATE INDEX idx_poa_representative ON powers_of_attorney(representative_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);

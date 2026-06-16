# SIMDAMA - Sistem Informasi Manajemen Data Mahasiswa
## Universitas Pamulang (UNPAM)

## Cara Install & Jalankan

### 1. Install Python 3.10+
Download: https://www.python.org/downloads/
✅ Centang "Add Python to PATH" saat install

### 2. Install library (jalankan di CMD/Terminal)
```
pip install flask werkzeug
```

### 3. Jalankan aplikasi
```
cd simdama
python app.py
```

### 4. Buka browser
```
http://localhost:5000
```

## Akun Login Demo
| Username | Password | Role  |
|----------|----------|-------|
| admin    | admin123 | Admin |
| dosen    | dosen123 | Dosen |

## Untuk Hosting (Pythonanywhere / Railway / Render)
- Upload seluruh folder simdama/
- Install requirements: `pip install -r requirements.txt`
- Set environment variable: `SECRET_KEY=your_secret_key`
- Entry point: `app.py`, function: `app`

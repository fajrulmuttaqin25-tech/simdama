"""
SIMDAMA - Sistem Informasi Manajemen Data Mahasiswa
Universitas Pamulang (UNPAM)
"""
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
from werkzeug.security import generate_password_hash, check_password_hash
import json, os, re, copy, csv
from io import StringIO
from datetime import datetime
from functools import wraps
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = "simdama_unpam_2024_secret"

@app.context_processor
def inject_globals():
    from datetime import datetime
    return {"now": datetime.now().strftime("%d %B %Y, %H:%M")}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data_mahasiswa.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

PRODI_LIST = [
    "Teknik Informatika","Sistem Informasi","Manajemen","Akuntansi",
    "Hukum","Teknik Industri","Pendidikan Bahasa Inggris",
    "Ilmu Komunikasi","Administrasi Publik","Teknik Elektro"
]

class ValidationError(Exception): pass
class DuplicateNIMError(Exception): pass

class Validator:
    NIM_PATTERN = re.compile(r"^\d{10,12}$")
    NAMA_PATTERN = re.compile(r"^[A-Za-z\s\.\,\']{3,60}$")
    EMAIL_PATTERN = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$")
    NO_HP_PATTERN = re.compile(r"^(\+62|62|0)[0-9]{8,12}$")

    @classmethod
    def validate_all(cls, nim, nama, email, no_hp, ipk, semester, is_edit=False):
        if not is_edit:
            if not cls.NIM_PATTERN.match(nim.strip()):
                raise ValidationError("NIM harus 10–12 digit angka.")
        if not cls.NAMA_PATTERN.match(nama.strip()):
            raise ValidationError("Nama hanya boleh huruf dan spasi (3–60 karakter).")
        if not cls.EMAIL_PATTERN.match(email.strip()):
            raise ValidationError("Format email tidak valid.")
        if not cls.NO_HP_PATTERN.match(no_hp.strip()):
            raise ValidationError("No HP tidak valid.")
        try:
            ipk_f = float(ipk)
            if not (0.0 <= ipk_f <= 4.0):
                raise ValidationError("IPK harus antara 0.00 – 4.00.")
        except ValueError:
            raise ValidationError("IPK harus berupa angka desimal.")
        try:
            sem = int(semester)
            if not (1 <= sem <= 14):
                raise ValidationError("Semester harus antara 1 – 14.")
        except ValueError:
            raise ValidationError("Semester harus berupa angka bulat.")

def baca_mahasiswa():
    try:
        if not os.path.exists(DATA_FILE):
            return []
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def simpan_mahasiswa(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def baca_users():
    default = {
        "admin": {"password": generate_password_hash("admin123"), "role": "Admin", "nama": "Administrator"},
        "dosen": {"password": generate_password_hash("dosen123"), "role": "Dosen", "nama": "Dosen UNPAM"},
    }
    
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data_mahasiswa = json.load(f)
                for mhs in data_mahasiswa:
                    nim = mhs.get("nim")
                    nama = mhs.get("nama")
                    if nim and nim not in default:
                        default[nim] = {
                            "password": generate_password_hash(f"{nim}123"),
                            "role": "Mahasiswa",
                            "nama": nama
                        }
    except Exception as e:
        print(f"Error loading mahasiswa for login: {e}")
    
    try:
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, "w") as f:
                json.dump(default, f, indent=2)
            return default
        with open(USERS_FILE, "r") as f:
            file_users = json.load(f)
            for k, v in default.items():
                if k not in file_users:
                    file_users[k] = v
            return file_users
    except Exception:
        return default

def linear_search(data, keyword, field):
    return [m for m in data if keyword.lower() in str(m.get(field,"")).lower()]

def binary_search(data, nim_target):
    arr = sorted(data, key=lambda m: m["nim"])
    lo, hi = 0, len(arr)-1
    while lo <= hi:
        mid = (lo+hi)//2
        if arr[mid]["nim"] == nim_target:
            return arr[mid]
        elif arr[mid]["nim"] < nim_target:
            lo = mid+1
        else:
            hi = mid-1
    return None

def sequential_search(data, nim_target):
    for m in data:
        if m["nim"] == nim_target:
            return m
    return None

def get_val(m, key):
    v = m.get(key, "")
    try:
        return float(v)
    except:
        return str(v).lower()

def bubble_sort(data, key, reverse=False):
    arr = copy.deepcopy(data)
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            cond = get_val(arr[j], key) > get_val(arr[j+1], key)
            if reverse:
                cond = not cond
            if cond:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr

def insertion_sort(data, key, reverse=False):
    arr = copy.deepcopy(data)
    for i in range(1, len(arr)):
        cur = arr[i]
        j = i-1
        while j >= 0 and ((not reverse and get_val(arr[j],key) > get_val(cur,key)) or
                          (reverse and get_val(arr[j],key) < get_val(cur,key))):
            arr[j+1] = arr[j]
            j -= 1
        arr[j+1] = cur
    return arr

def selection_sort(data, key, reverse=False):
    arr = copy.deepcopy(data)
    n = len(arr)
    for i in range(n):
        idx = i
        for j in range(i+1, n):
            cond = get_val(arr[j],key) < get_val(arr[idx],key)
            if reverse:
                cond = get_val(arr[j],key) > get_val(arr[idx],key)
            if cond:
                idx = j
        arr[i], arr[idx] = arr[idx], arr[i]
    return arr

def merge_sort(data, key, reverse=False):
    if len(data) <= 1:
        return data[:]
    mid = len(data)//2
    L = merge_sort(data[:mid], key, reverse)
    R = merge_sort(data[mid:], key, reverse)
    result, i, j = [], 0, 0
    while i < len(L) and j < len(R):
        cond = get_val(L[i],key) <= get_val(R[j],key)
        if reverse:
            cond = get_val(L[i],key) >= get_val(R[j],key)
        if cond:
            result.append(L[i])
            i += 1
        else:
            result.append(R[j])
            j += 1
    result.extend(L[i:])
    result.extend(R[j:])
    return result

def shell_sort(data, key, reverse=False):
    arr = copy.deepcopy(data)
    n = len(arr)
    gap = n//2
    while gap > 0:
        for i in range(gap, n):
            temp = arr[i]
            j = i
            while j >= gap and ((not reverse and get_val(arr[j-gap],key) > get_val(temp,key)) or
                                (reverse and get_val(arr[j-gap],key) < get_val(temp,key))):
                arr[j] = arr[j-gap]
                j -= gap
            arr[j] = temp
        gap //= 2
    return arr

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            flash("Silakan login terlebih dahulu.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ==================== ROUTES ====================

@app.route("/", methods=["GET","POST"])
def login():
    if "username" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","").strip()
        users = baca_users()
        
        try:
            if not username or not password:
                raise ValidationError("Username dan password tidak boleh kosong.")
            
            if username not in users:
                raise ValidationError("Username/NIM tidak ditemukan.")
            
            u = users[username]
            try:
                pwd_ok = check_password_hash(u["password"], password)
            except Exception:
                pwd_ok = (u["password"] == password)
            
            if not pwd_ok:
                raise ValidationError("Password salah. Coba lagi.")
            
            session["username"] = username
            session["role"] = u["role"]
            session["nama"] = u.get("nama", username)
            
            return redirect(url_for("dashboard"))
        except ValidationError as e:
            error = str(e)
    
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    data = baca_mahasiswa()
    n = len(data)
    avg_ipk = round(sum(float(m.get("ipk",0)) for m in data)/n, 2) if n else 0
    max_ipk = round(max((float(m.get("ipk",0)) for m in data), default=0), 2)
    min_ipk = round(min((float(m.get("ipk",0)) for m in data), default=0), 2)
    prodi_count = {}
    for m in data:
        prodi_count[m["prodi"]] = prodi_count.get(m["prodi"], 0) + 1
    recent = list(reversed(data[-6:])) if data else []
    return render_template("dashboard.html",
        total=n, avg_ipk=avg_ipk, max_ipk=max_ipk, min_ipk=min_ipk,
        prodi_count=sorted(prodi_count.items(), key=lambda x:-x[1]),
        recent=recent)

@app.route("/mahasiswa")
@login_required
def mahasiswa():
    data = baca_mahasiswa()
    q = request.args.get("q","").strip()
    if q:
        data = [m for m in data if
                q.lower() in m.get("nim","").lower() or
                q.lower() in m.get("nama","").lower() or
                q.lower() in m.get("prodi","").lower()]
    return render_template("mahasiswa.html", data=data, q=q, total=len(data))

@app.route("/mahasiswa/tambah", methods=["GET","POST"])
@login_required
def tambah():
    error = None
    form_data = {}
    if request.method == "POST":
        form_data = request.form.to_dict()
        try:
            nim = request.form.get("nim","").strip()
            nama = request.form.get("nama","").strip()
            email = request.form.get("email","").strip()
            no_hp = request.form.get("no_hp","").strip()
            ipk = request.form.get("ipk","").strip()
            prodi = request.form.get("prodi","").strip()
            semester = request.form.get("semester","").strip()
            Validator.validate_all(nim, nama, email, no_hp, ipk, semester)
            data = baca_mahasiswa()
            if any(m["nim"] == nim for m in data):
                raise DuplicateNIMError(f"NIM {nim} sudah terdaftar.")
            data.append({
                "nim": nim, "nama": nama, "prodi": prodi,
                "semester": int(semester), "ipk": float(ipk),
                "email": email, "no_hp": no_hp,
                "tgl_daftar": datetime.now().strftime("%d-%m-%Y %H:%M")
            })
            simpan_mahasiswa(data)
            
            users = baca_users()
            if nim not in users:
                users[nim] = {
                    "password": generate_password_hash(f"{nim}123"),
                    "role": "Mahasiswa",
                    "nama": nama
                }
                with open(USERS_FILE, "w") as f:
                    json.dump(users, f, indent=2)
            
            flash(f"✅ Mahasiswa {nama} berhasil ditambahkan!", "success")
            return redirect(url_for("mahasiswa"))
        except (ValidationError, DuplicateNIMError) as e:
            error = str(e)
    return render_template("form.html", mode="tambah", prodi_list=PRODI_LIST,
                           data=form_data, error=error)

@app.route("/mahasiswa/edit/<path:nim>", methods=["GET","POST"])
@login_required
def edit(nim):
    nim = nim.strip()
    all_data = baca_mahasiswa()
    mhs = next((m for m in all_data if str(m["nim"]).strip() == nim), None)
    if not mhs:
        flash("❌ Mahasiswa tidak ditemukan.", "error")
        return redirect(url_for("mahasiswa"))
    error = None
    if request.method == "POST":
        try:
            nama = request.form.get("nama","").strip()
            email = request.form.get("email","").strip()
            no_hp = request.form.get("no_hp","").strip()
            ipk = request.form.get("ipk","").strip()
            prodi = request.form.get("prodi","").strip()
            semester = request.form.get("semester","").strip()
            Validator.validate_all(nim, nama, email, no_hp, ipk, semester, is_edit=True)
            for m in all_data:
                if str(m["nim"]).strip() == nim:
                    m["nama"] = nama
                    m["prodi"] = prodi
                    m["semester"] = int(semester)
                    m["ipk"] = float(ipk)
                    m["email"] = email
                    m["no_hp"] = no_hp
                    break
            simpan_mahasiswa(all_data)
            
            users = baca_users()
            if nim in users:
                users[nim]["nama"] = nama
                with open(USERS_FILE, "w") as f:
                    json.dump(users, f, indent=2)
            
            flash(f"✅ Data {nama} berhasil diperbarui!", "success")
            return redirect(url_for("mahasiswa"))
        except ValidationError as e:
            error = str(e)
            mhs = request.form.to_dict()
            mhs["nim"] = nim
    return render_template("form.html", mode="edit", prodi_list=PRODI_LIST,
                           data=mhs, error=error)

@app.route("/mahasiswa/hapus/<path:nim>", methods=["POST"])
@login_required
def hapus(nim):
    nim = nim.strip()
    all_data = baca_mahasiswa()
    baru = [m for m in all_data if str(m["nim"]).strip() != nim]
    if len(baru) == len(all_data):
        flash("❌ Mahasiswa tidak ditemukan.", "error")
    else:
        simpan_mahasiswa(baru)
        
        users = baca_users()
        if nim in users:
            del users[nim]
            with open(USERS_FILE, "w") as f:
                json.dump(users, f, indent=2)
        
        flash("✅ Data mahasiswa berhasil dihapus.", "success")
    return redirect(url_for("mahasiswa"))

@app.route("/cari", methods=["GET","POST"])
@login_required
def cari():
    hasil, info, keyword, algo, field = [], "", "", "linear", "nama"
    
    if request.method == "POST":
        keyword = request.form.get("keyword","").strip()
        algo = request.form.get("algo","linear")
        field = request.form.get("field","nama")
        data = baca_mahasiswa()
        try:
            if not keyword:
                raise ValidationError("Masukkan kata kunci pencarian.")
            
            import time
            
            if algo == "linear":
                start = time.perf_counter()
                hasil = linear_search(data, keyword, field)
                end = time.perf_counter()
                waktu = (end - start) * 1_000_000
                waktu_eksekusi = f"{waktu:.2f} µs" if waktu < 1000 else f"{waktu/1000:.2f} ms"
                info = f"Linear Search &mdash; <b>{len(hasil)} hasil</b> ditemukan"
                
            elif algo == "binary":
                start = time.perf_counter()
                found = binary_search(data, keyword)
                end = time.perf_counter()
                waktu = (end - start) * 1_000_000
                waktu_eksekusi = f"{waktu:.2f} µs" if waktu < 1000 else f"{waktu/1000:.2f} ms"
                hasil = [found] if found else []
                info = f"Binary Search &mdash; <b>{'1 hasil' if found else '0 hasil'}</b> ditemukan"
                
            else:
                start = time.perf_counter()
                found = sequential_search(data, keyword)
                end = time.perf_counter()
                waktu = (end - start) * 1_000_000
                waktu_eksekusi = f"{waktu:.2f} µs" if waktu < 1000 else f"{waktu/1000:.2f} ms"
                hasil = [found] if found else []
                info = f"Sequential Search &mdash; <b>{'1 hasil' if found else '0 hasil'}</b> ditemukan"
                
            info += f"&nbsp;|&nbsp; ⏱️ Waktu eksekusi: <b>{waktu_eksekusi}</b>"
            
        except ValidationError as e:
            flash(str(e), "error")
    
    return render_template("cari.html", hasil=hasil, info=info,
                           keyword=keyword, algo=algo, field=field)

@app.route("/sort", methods=["GET","POST"])
@login_required
def sort_data():
    data = baca_mahasiswa()
    hasil = data[:]
    algo, key, order, info = "bubble", "nim", "asc", ""
    
    if request.method == "POST":
        algo = request.form.get("algo","bubble")
        key = request.form.get("key","nim")
        order = request.form.get("order","asc")
        rev = (order == "desc")
        
        algo_map = {"bubble":bubble_sort,"insertion":insertion_sort,
                    "selection":selection_sort,"merge":merge_sort,"shell":shell_sort}
        complexity = {"bubble":"O(n²)","insertion":"O(n²)","selection":"O(n²)",
                      "merge":"O(n log n)","shell":"O(n log n)"}
        
        import time
        start = time.perf_counter()
        hasil = algo_map.get(algo, bubble_sort)(data, key, rev)
        end = time.perf_counter()
        waktu = (end - start) * 1_000_000
        waktu_eksekusi = f"{waktu:.2f} µs" if waktu < 1000 else f"{waktu/1000:.2f} ms"
        
        asc_desc = "Descending ↓" if rev else "Ascending ↑"
        info = f"{algo.capitalize()} Sort &nbsp;|&nbsp; Kunci: <b>{key}</b> &nbsp;|&nbsp; {asc_desc} &nbsp;|&nbsp; Complexity: <code>{complexity[algo]}</code>"
        info += f"&nbsp;|&nbsp; ⏱️ Waktu eksekusi: <b>{waktu_eksekusi}</b>"
    
    return render_template("sort.html", hasil=hasil, algo=algo,
                           key=key, order=order, info=info)

@app.route("/complexity")
@login_required
def complexity():
    return render_template("complexity.html")

# ==================== ROUTE IMPORT MAHASISWA ====================

@app.route("/mahasiswa/import", methods=["GET", "POST"])
@login_required
def import_mahasiswa():
    if request.method == "POST":
        if 'file' not in request.files:
            flash("❌ Pilih file terlebih dahulu", "error")
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash("❌ File tidak dipilih", "error")
            return redirect(request.url)
        
        if not file.filename.endswith('.csv'):
            flash("❌ Hanya file CSV yang didukung", "error")
            return redirect(request.url)
        
        try:
            content = file.read().decode('utf-8')
            lines = content.strip().split('\n')
            
            if len(lines) < 2:
                flash("❌ File kosong", "error")
                return redirect(request.url)
            
            existing_data = baca_mahasiswa()
            existing_nims = [m['nim'] for m in existing_data]
            success_count = 0
            error_count = 0
            
            for idx, line in enumerate(lines[1:], start=2):
                if not line.strip():
                    continue
                
                values = line.strip().split(',')
                
                if len(values) < 7:
                    error_count += 1
                    continue
                
                nim = values[0].strip()
                nama = values[1].strip()
                email = values[2].strip() if len(values) > 2 else ''
                no_hp = values[3].strip() if len(values) > 3 else ''
                prodi = values[4].strip() if len(values) > 4 else 'Teknik Informatika'
                semester = values[5].strip() if len(values) > 5 else '1'
                ipk = values[6].strip() if len(values) > 6 else '0'
                
                if not nim or not nama:
                    error_count += 1
                    continue
                
                if nim in existing_nims:
                    error_count += 1
                    continue
                
                existing_data.append({
                    'nim': nim,
                    'nama': nama,
                    'prodi': prodi,
                    'semester': int(semester) if semester.isdigit() else 1,
                    'ipk': float(ipk) if ipk else 0,
                    'email': email,
                    'no_hp': no_hp,
                    'tgl_daftar': datetime.now().strftime("%d-%m-%Y %H:%M")
                })
                success_count += 1
                existing_nims.append(nim)
            
            simpan_mahasiswa(existing_data)
            
            users = baca_users()
            for mhs in existing_data[-success_count:]:
                nim = mhs.get('nim')
                nama = mhs.get('nama')
                if nim and nim not in users:
                    users[nim] = {
                        "password": generate_password_hash(f"{nim}123"),
                        "role": "Mahasiswa",
                        "nama": nama
                    }
            with open(USERS_FILE, "w") as f:
                json.dump(users, f, indent=2)
            
            if success_count > 0:
                flash(f"✅ Berhasil import {success_count} mahasiswa", "success")
            if error_count > 0:
                flash(f"⚠️ {error_count} baris gagal diimport", "error")
            
            return redirect(url_for('mahasiswa'))
            
        except Exception as e:
            flash(f"❌ Error: {str(e)}", "error")
            return redirect(request.url)
    
    return render_template("import_mahasiswa.html")

@app.route("/check-status")
@login_required
def check_status():
    return jsonify({"status": "ok"})

# ==================== ROUTE EKSPOR DATA ====================

@app.route("/ekspor/csv")
@login_required
def ekspor_csv():
    data = baca_mahasiswa()
    
    if not data:
        flash("❌ Tidak ada data untuk diekspor", "error")
        return redirect(url_for("mahasiswa"))
    
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['NIM', 'Nama', 'Program Studi', 'Semester', 'IPK', 'Email', 'No HP', 'Tanggal Daftar'])
    
    for m in data:
        writer.writerow([
            m.get('nim', ''),
            m.get('nama', ''),
            m.get('prodi', ''),
            m.get('semester', ''),
            m.get('ipk', ''),
            m.get('email', ''),
            m.get('no_hp', ''),
            m.get('tgl_daftar', '')
        ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=Data_Mahasiswa_{datetime.now().strftime("%Y%m%d")}.csv'}
    )

@app.route("/ekspor/json")
@login_required
def ekspor_json():
    data = baca_mahasiswa()
    
    if not data:
        flash("❌ Tidak ada data untuk diekspor", "error")
        return redirect(url_for("mahasiswa"))
    
    return Response(
        json.dumps(data, indent=2, ensure_ascii=False),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename=Data_Mahasiswa_{datetime.now().strftime("%Y%m%d")}.json'}
    )

# ==================== ROUTE KIRIM EMAIL (SEMUA MAHASISWA) ====================

@app.route("/send-email", methods=["GET", "POST"])
@login_required
def send_email():
    data = baca_mahasiswa()
    
    if session.get("role") not in ["Admin", "Dosen"]:
        flash("❌ Hanya Admin dan Dosen yang dapat mengirim email", "error")
        return redirect(url_for("dashboard"))
    
    if request.method == "POST":
        try:
            subject = request.form.get("subject", "").strip()
            message_template = request.form.get("message", "").strip()
            
            if not subject or not message_template:
                flash("❌ Subject dan pesan harus diisi", "error")
                return redirect(url_for("send_email"))
            
            EMAIL_SENDER = os.getenv("EMAIL_SENDER")
            EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

            SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp-relay.brevo.com")
            SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
            
            success_count = 0
            fail_count = 0
            error_log = []
            
            for mhs in data:
                email_mhs = mhs.get("email", "").strip()
                if not email_mhs:
                    fail_count += 1
                    error_log.append(f"{mhs.get('nama')} - Email kosong")
                    continue
                
                try:
                    # Ganti placeholder
                    body = message_template
                    body = body.replace("[NAMA]", mhs.get("nama", ""))
                    body = body.replace("[NIM]", mhs.get("nim", ""))
                    body = body.replace("[PRODI]", mhs.get("prodi", ""))
                    body = body.replace("[SEMESTER]", str(mhs.get("semester", "")))
                    body = body.replace("[IPK]", str(mhs.get("ipk", "")))
                    
                    # HTML Version
                    html_body = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                        <p>Yth. {mhs.get('nama', '')},</p>
                        <p>Kami dari Sistem Informasi Manajemen Data Mahasiswa (SIMDAMA) Universitas Pamulang (UNPAM) menginformasikan bahwa data Anda telah terdaftar dalam sistem kami.</p>
                        <p><b>Berikut data Anda:</b></p>
                        <ul>
                            <li><b>NIM:</b> {mhs.get('nim', '')}</li>
                            <li><b>Program Studi:</b> {mhs.get('prodi', '')}</li>
                            <li><b>Semester:</b> {mhs.get('semester', '')}</li>
                            <li><b>IPK:</b> {mhs.get('ipk', '')}</li>
                        </ul>
                        <p>Untuk informasi lebih lanjut, silahkan login ke sistem SIMDAMA menggunakan:</p>
                        <p><b>Username:</b> {mhs.get('nim', '')}<br>
                        <b>Password:</b> {mhs.get('nim', '')}123</p>
                        <p>Terima kasih atas perhatiannya.</p>
                        <p>Salam,<br>
                        <b>Tim SIMDAMA UNPAM</b></p>
                        <hr>
                        <small style="color: #888;">Email ini dikirim secara otomatis oleh sistem SIMDAMA UNPAM.</small>
                    </body>
                    </html>
                    """
                    
                    msg = MIMEMultipart('alternative')
                    msg['From'] = f"SIMDAMA UNPAM <{EMAIL_SENDER}>"
                    msg['To'] = email_mhs
                    msg['Subject'] = f"{subject} - {mhs.get('nama')}"
                    
                    msg.attach(MIMEText(body, 'plain'))
                    msg.attach(MIMEText(html_body, 'html'))
                    
                    server = smtplib.SMTP(
                        SMTP_SERVER,
                        SMTP_PORT,
                        timeout=15
                    )
                    server.starttls()
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                    try:
                        server.send_message(msg)
                    except Exception as e:
                        flash(f"Gagal mengirim email: {e}", "danger")
                        return redirect(request.url)
                    finally:
                        server.quit()
                    server.quit()
                    success_count += 1
                    
                except Exception as e:
                    fail_count += 1
                    error_log.append(f"{mhs.get('nama')} - {str(e)[:50]}")
            
            if success_count > 0:
                flash(f"✅ Berhasil mengirim ke {success_count} mahasiswa", "success")
            if fail_count > 0:
                flash(f"❌ Gagal mengirim ke {fail_count} mahasiswa", "error")
                if error_log:
                    flash(f"Detail: {', '.join(error_log[:3])}", "error")
            
            return redirect(url_for("send_email"))
            
        except Exception as e:
            flash(f"❌ Error: {str(e)}", "error")
            return redirect(url_for("send_email"))
    
    return render_template("send_email.html", data=data, total=len(data))

# ==================== ROUTE KIRIM EMAIL PER MAHASISWA (FIX SPAM) ====================

@app.route("/send-email/<nim>", methods=["GET", "POST"])
@login_required
def send_email_specific(nim):
    nim = nim.strip()
    all_data = baca_mahasiswa()
    mhs = next((m for m in all_data if str(m["nim"]).strip() == nim), None)
    
    if not mhs:
        flash("❌ Mahasiswa tidak ditemukan.", "error")
        return redirect(url_for("mahasiswa"))
    
    if session.get("role") not in ["Admin", "Dosen"]:
        flash("❌ Hanya Admin dan Dosen yang dapat mengirim email", "error")
        return redirect(url_for("dashboard"))
    
    if not mhs.get("email") or mhs.get("email") == "":
        flash(f"❌ Mahasiswa {mhs.get('nama')} tidak memiliki email!", "error")
        return redirect(url_for("mahasiswa"))
    
    if request.method == "POST":
        try:
            subject = request.form.get("subject", "").strip()
            message_template = request.form.get("message", "").strip()
            
            if not subject or not message_template:
                flash("❌ Subject dan pesan harus diisi", "error")
                return render_template("send_email_specific.html", mhs=mhs)
            
            EMAIL_SENDER = "fajrulmuttaqin25@gmail.com"
            EMAIL_PASSWORD = "scpz qeev ybli hrfc"
            
            SMTP_SERVER = "smtp.gmail.com"
            SMTP_PORT = 587
            
            email_mhs = mhs.get("email", "").strip()
            
            # Ganti placeholder
            body = message_template
            body = body.replace("[NAMA]", mhs.get("nama", ""))
            body = body.replace("[NIM]", mhs.get("nim", ""))
            body = body.replace("[PRODI]", mhs.get("prodi", ""))
            body = body.replace("[SEMESTER]", str(mhs.get("semester", "")))
            body = body.replace("[IPK]", str(mhs.get("ipk", "")))
            
            # HTML Version
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <p>Yth. {mhs.get('nama', '')},</p>
                <p>Kami dari Sistem Informasi Manajemen Data Mahasiswa (SIMDAMA) Universitas Pamulang (UNPAM) menginformasikan bahwa data Anda telah terdaftar dalam sistem kami.</p>
                <p><b>Berikut data Anda:</b></p>
                <ul>
                    <li><b>NIM:</b> {mhs.get('nim', '')}</li>
                    <li><b>Program Studi:</b> {mhs.get('prodi', '')}</li>
                    <li><b>Semester:</b> {mhs.get('semester', '')}</li>
                    <li><b>IPK:</b> {mhs.get('ipk', '')}</li>
                </ul>
                <p>Untuk informasi lebih lanjut, silahkan login ke sistem SIMDAMA menggunakan:</p>
                <p><b>Username:</b> {mhs.get('nim', '')}<br>
                <b>Password:</b> {mhs.get('nim', '')}123</p>
                <p>Terima kasih atas perhatiannya.</p>
                <p>Salam,<br>
                <b>Tim SIMDAMA UNPAM</b></p>
                <hr>
                <small style="color: #888;">Email ini dikirim secara otomatis oleh sistem SIMDAMA UNPAM.</small>
            </body>
            </html>
            """
            
            try:
                msg = MIMEMultipart('alternative')
                msg['From'] = f"SIMDAMA UNPAM <{EMAIL_SENDER}>"
                msg['To'] = email_mhs
                msg['Subject'] = f"{subject} - {mhs.get('nama')}"
                
                msg.attach(MIMEText(body, 'plain'))
                msg.attach(MIMEText(html_body, 'html'))
                
                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                server.starttls()
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(msg)
                server.quit()
                
                flash(f"✅ Email berhasil dikirim ke {mhs.get('nama')} ({email_mhs})", "success")
                return redirect(url_for("mahasiswa"))
                
            except Exception as e:
                flash(f"❌ Gagal mengirim email ke {mhs.get('nama')}: {str(e)}", "error")
                return render_template("send_email_specific.html", mhs=mhs)
            
        except Exception as e:
            flash(f"❌ Error: {str(e)}", "error")
            return render_template("send_email_specific.html", mhs=mhs)
    
    # Buat pesan default
    default_message = f"""Yth. {mhs.get('nama', '')},

Kami dari Sistem Informasi Manajemen Data Mahasiswa (SIMDAMA) Universitas Pamulang (UNPAM) menginformasikan bahwa data Anda telah terdaftar dalam sistem kami.

Berikut data Anda:
• NIM: {mhs.get('nim', '')}
• Program Studi: {mhs.get('prodi', '')}
• Semester: {mhs.get('semester', '')}
• IPK: {mhs.get('ipk', '')}

Untuk informasi lebih lanjut, silahkan login ke sistem SIMDAMA menggunakan:
Username: {mhs.get('nim', '')}
Password: {mhs.get('nim', '')}123

Terima kasih atas perhatiannya.

Salam,
Tim SIMDAMA UNPAM"""
    
    return render_template("send_email_specific.html", mhs=mhs, default_message=default_message)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
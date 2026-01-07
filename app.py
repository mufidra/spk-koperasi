from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from database import db, login_manager
from models import User, Nasabah, Kriteria, NilaiNasabah
import os
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'spk-koperasi-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spk_koperasi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inisialisasi database dan login manager
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Silakan login untuk mengakses halaman ini.'
login_manager.login_message_category = 'warning'

# User loader untuk Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========== CONTEXT PROCESSOR ==========
@app.context_processor
def inject_user_and_version():
    """Inject user data dan version ke semua template"""
    return {
        'current_user': current_user,
        'css_version': int(time.time())
    }

# ========== ROUTES AUTHENTIKASI ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Halaman login"""
    # Jika user sudah login, redirect ke dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = 'remember' in request.form
        
        # Cari user
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if user.is_active:
                login_user(user, remember=remember)
                flash('Login berhasil! Selamat datang.', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Akun Anda tidak aktif.', 'danger')
        else:
            flash('Username atau password salah.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    """Halaman profile user"""
    return render_template('profile.html', user=current_user)

@app.route('/ubah-password', methods=['POST'])
@login_required
def ubah_password():
    """Ubah password user"""
    password_lama = request.form.get('password_lama')
    password_baru = request.form.get('password_baru')
    konfirmasi = request.form.get('konfirmasi')
    
    if not current_user.check_password(password_lama):
        flash('Password lama salah!', 'danger')
    elif password_baru != konfirmasi:
        flash('Konfirmasi password tidak cocok!', 'danger')
    elif len(password_baru) < 6:
        flash('Password baru minimal 6 karakter!', 'danger')
    else:
        current_user.set_password(password_baru)
        db.session.commit()
        flash('Password berhasil diubah!', 'success')
    
    return redirect(url_for('profile'))

# ========== HAPUS MIDDLEWARE UNTUK HINDARI RECURSION ==========
# Middleware before_request dihapus karena menyebabkan recursion dengan Flask-Login
# Biarkan Flask-Login menangani proteksi otomatis dengan @login_required

# ========== ROUTES UTAMA ==========
@app.route('/')
@login_required
def dashboard():
    total_nasabah = Nasabah.query.count()
    total_kriteria = Kriteria.query.count()
    kriterias = Kriteria.query.all()
    return render_template('dashboard.html', 
                         total_nasabah=total_nasabah,
                         total_kriteria=total_kriteria,
                         kriterias=kriterias)

# ========== DATA ALTERNATIF ==========
@app.route('/alternatif')
@login_required
def alternatif():
    nasabahs = Nasabah.query.all()
    return render_template('alternatif.html', nasabahs=nasabahs)

@app.route('/alternatif/tambah', methods=['GET', 'POST'])
@login_required
def tambah_alternatif():
    kriterias = Kriteria.query.all()
    
    if request.method == 'POST':
        kode = request.form['kode']
        nama = request.form['nama']
        alamat = request.form['alamat']
        telepon = request.form['telepon']
        
        # Cek apakah kode sudah ada
        if Nasabah.query.filter_by(kode=kode).first():
            flash('Kode nasabah sudah ada!', 'danger')
            return redirect(url_for('tambah_alternatif'))
        
        nasabah = Nasabah(kode=kode, nama=nama, alamat=alamat, telepon=telepon)
        db.session.add(nasabah)
        db.session.commit()
        
        # Input nilai untuk kriteria C1-C5
        for kriteria in kriterias:
            nilai_key = f'nilai_{kriteria.kode}'
            if nilai_key in request.form and request.form[nilai_key]:
                try:
                    nilai = float(request.form[nilai_key])
                    nilai_nasabah = NilaiNasabah(
                        nasabah_id=nasabah.id,
                        kriteria_id=kriteria.id,
                        nilai=nilai
                    )
                    db.session.add(nilai_nasabah)
                except ValueError:
                    flash(f'Nilai untuk {kriteria.nama} tidak valid!', 'warning')
        
        db.session.commit()
        flash('Nasabah berhasil ditambahkan!', 'success')
        return redirect(url_for('alternatif'))
    
    return render_template('alternatif_form.html', action='Tambah', kriterias=kriterias)

@app.route('/alternatif/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_alternatif(id):
    nasabah = Nasabah.query.get_or_404(id)
    kriterias = Kriteria.query.all()
    
    if request.method == 'POST':
        nasabah.kode = request.form['kode']
        nasabah.nama = request.form['nama']
        nasabah.alamat = request.form['alamat']
        nasabah.telepon = request.form['telepon']
        
        # Update nilai untuk kriteria
        for kriteria in kriterias:
            nilai_key = f'nilai_{kriteria.kode}'
            if nilai_key in request.form and request.form[nilai_key]:
                try:
                    nilai = float(request.form[nilai_key])
                    # Cek apakah nilai sudah ada
                    nilai_nasabah = NilaiNasabah.query.filter_by(
                        nasabah_id=nasabah.id,
                        kriteria_id=kriteria.id
                    ).first()
                    
                    if nilai_nasabah:
                        nilai_nasabah.nilai = nilai
                    else:
                        nilai_nasabah = NilaiNasabah(
                            nasabah_id=nasabah.id,
                            kriteria_id=kriteria.id,
                            nilai=nilai
                        )
                        db.session.add(nilai_nasabah)
                except ValueError:
                    flash(f'Nilai untuk {kriteria.nama} tidak valid!', 'warning')
        
        db.session.commit()
        flash('Nasabah berhasil diupdate!', 'success')
        return redirect(url_for('alternatif'))
    
    # Ambil nilai yang sudah ada
    nilai_dict = {}
    for nilai in nasabah.nilai:
        nilai_dict[nilai.kriteria.kode] = nilai.nilai
    
    return render_template('alternatif_form.html', nasabah=nasabah, action='Edit', kriterias=kriterias, nilai_dict=nilai_dict)

@app.route('/alternatif/hapus/<int:id>')
@login_required
def hapus_alternatif(id):
    nasabah = Nasabah.query.get_or_404(id)
    db.session.delete(nasabah)
    db.session.commit()
    flash('Nasabah berhasil dihapus!', 'success')
    return redirect(url_for('alternatif'))

# ========== DATA KRITERIA (CRUD) ==========
@app.route('/kriteria')
@login_required
def kriteria():
    kriterias = Kriteria.query.order_by(Kriteria.kode).all()
    return render_template('kriteria.html', kriterias=kriterias)

@app.route('/kriteria/tambah', methods=['GET', 'POST'])
@login_required
def tambah_kriteria():
    if request.method == 'POST':
        kode = request.form['kode']
        nama = request.form['nama']
        atribut = request.form['atribut']
        bobot = float(request.form['bobot'])
        keterangan = request.form.get('keterangan', '')
        
        # Cek apakah kode sudah ada
        if Kriteria.query.filter_by(kode=kode).first():
            flash('Kode kriteria sudah ada!', 'danger')
            return redirect(url_for('tambah_kriteria'))
        
        kriteria = Kriteria(
            kode=kode,
            nama=nama,
            atribut=atribut,
            bobot=bobot,
            keterangan=keterangan
        )
        db.session.add(kriteria)
        db.session.commit()
        
        flash('Kriteria berhasil ditambahkan!', 'success')
        return redirect(url_for('kriteria'))
    
    return render_template('kriteria_form.html', action='Tambah')

@app.route('/kriteria/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_kriteria(id):
    kriteria = Kriteria.query.get_or_404(id)
    
    if request.method == 'POST':
        kriteria.kode = request.form['kode']
        kriteria.nama = request.form['nama']
        kriteria.atribut = request.form['atribut']
        kriteria.bobot = float(request.form['bobot'])
        kriteria.keterangan = request.form.get('keterangan', '')
        
        db.session.commit()
        flash('Kriteria berhasil diupdate!', 'success')
        return redirect(url_for('kriteria'))
    
    return render_template('kriteria_form.html', kriteria=kriteria, action='Edit')

@app.route('/kriteria/hapus/<int:id>')
@login_required
def hapus_kriteria(id):
    kriteria = Kriteria.query.get_or_404(id)
    # Cek apakah kriteria digunakan
    if NilaiNasabah.query.filter_by(kriteria_id=kriteria.id).first():
        flash('Kriteria tidak bisa dihapus karena sudah digunakan!', 'danger')
    else:
        db.session.delete(kriteria)
        db.session.commit()
        flash('Kriteria berhasil dihapus!', 'success')
    return redirect(url_for('kriteria'))

# ========== BOBOT KRITERIA ==========
@app.route('/bobot')
@login_required
def bobot():
    kriterias = Kriteria.query.order_by(Kriteria.kode).all()
    total_bobot = sum([k.bobot for k in kriterias])
    return render_template('bobot.html', kriterias=kriterias, total_bobot=total_bobot)

@app.route('/bobot/update', methods=['POST'])
@login_required
def update_bobot():
    if request.method == 'POST':
        kriterias = Kriteria.query.all()
        for kriteria in kriterias:
            bobot_key = f'bobot_{kriteria.id}'
            if bobot_key in request.form:
                kriteria.bobot = float(request.form[bobot_key])
        
        db.session.commit()
        flash('Bobot kriteria berhasil diupdate!', 'success')
        return redirect(url_for('bobot'))

# ========== NILAI ALTERNATIF ==========
@app.route('/nilai')
@login_required
def nilai_alternatif():
    nasabahs = Nasabah.query.all()
    kriterias = Kriteria.query.order_by(Kriteria.kode).all()
    
    # Buat dictionary untuk nilai
    nilai_dict = {}
    for nasabah in nasabahs:
        nilai_dict[nasabah.id] = {}
        for nilai in nasabah.nilai:
            nilai_dict[nasabah.id][nilai.kriteria_id] = nilai.nilai
    
    return render_template('nilai_alternatif.html', 
                         nasabahs=nasabahs, 
                         kriterias=kriterias,
                         nilai_dict=nilai_dict)

@app.route('/nilai/edit/<int:nasabah_id>', methods=['GET', 'POST'])
@login_required
def edit_nilai(nasabah_id):
    nasabah = Nasabah.query.get_or_404(nasabah_id)
    kriterias = Kriteria.query.order_by(Kriteria.kode).all()
    
    if request.method == 'POST':
        for kriteria in kriterias:
            nilai_key = f'nilai_{kriteria.id}'
            if nilai_key in request.form:
                try:
                    nilai = float(request.form[nilai_key])
                    
                    # Cek apakah nilai sudah ada
                    nilai_nasabah = NilaiNasabah.query.filter_by(
                        nasabah_id=nasabah_id,
                        kriteria_id=kriteria.id
                    ).first()
                    
                    if nilai_nasabah:
                        nilai_nasabah.nilai = nilai
                    else:
                        nilai_nasabah = NilaiNasabah(
                            nasabah_id=nasabah_id,
                            kriteria_id=kriteria.id,
                            nilai=nilai
                        )
                        db.session.add(nilai_nasabah)
                except ValueError:
                    flash(f'Nilai untuk {kriteria.nama} tidak valid!', 'warning')
        
        db.session.commit()
        flash('Nilai nasabah berhasil diupdate!', 'success')
        return redirect(url_for('nilai_alternatif'))
    
    # Ambil nilai yang sudah ada
    nilai_dict = {}
    for nilai in nasabah.nilai:
        nilai_dict[nilai.kriteria_id] = nilai.nilai
    
    return render_template('nilai_alternatif_form.html', 
                         nasabah=nasabah, 
                         kriterias=kriterias,
                         nilai_dict=nilai_dict)

# ========== PERHITUNGAN SAW ==========
@app.route('/saw')
@login_required
def perhitungan_saw():
    nasabahs = Nasabah.query.all()
    kriterias = Kriteria.query.order_by(Kriteria.kode).all()
    
    if not nasabahs or not kriterias:
        flash('Data belum lengkap!', 'warning')
        return redirect(url_for('dashboard'))
    
    # Ambil semua nilai
    semua_nilai = []
    for nasabah in nasabahs:
        nilai_row = {'nasabah': nasabah}
        for kriteria in kriterias:
            nilai_nasabah = NilaiNasabah.query.filter_by(
                nasabah_id=nasabah.id,
                kriteria_id=kriteria.id
            ).first()
            nilai_row[kriteria.id] = nilai_nasabah.nilai if nilai_nasabah else 0
        semua_nilai.append(nilai_row)
    
    # NILAI IDEAL dari SKALA VERSI BARU
    nilai_ideal = {
        'C1': {'max': 90, 'min': 60},  # Skala 60-90
        'C2': {'max': 85, 'min': 60},  # Skala 60-85  
        'C3': {'max': 70, 'min': 50},  # Skala 50-70 (COST)
        'C4': {'max': 75, 'min': 55},  # Skala 55-75
        'C5': {'max': 80, 'min': 60}   # Skala 60-80
    }
    
    # Normalisasi matriks
    matriks_normalisasi = []
    for row in semua_nilai:
        normalized_row = {'nasabah': row['nasabah']}
        for kriteria in kriterias:
            nilai = row[kriteria.id]
            ideal = nilai_ideal.get(kriteria.kode)
            
            if not ideal or nilai == 0:
                normalized_row[kriteria.id] = 0
            else:
                if kriteria.atribut == 'benefit':
                    # Benefit: r_ij = x_ij / max_ideal
                    max_val = ideal['max']
                    normalized_row[kriteria.id] = nilai / max_val if max_val > 0 else 0
                else:  # cost
                    # Cost: r_ij = min_ideal / x_ij
                    min_val = ideal['min']
                    normalized_row[kriteria.id] = min_val / nilai if nilai > 0 else 0
        
        matriks_normalisasi.append(normalized_row)
    
    # Hitung nilai preferensi
    hasil_perhitungan = []
    for i, row in enumerate(matriks_normalisasi):
        nasabah = row['nasabah']
        total_preferensi = 0
        
        for kriteria in kriterias:
            normalized = row[kriteria.id]
            preferensi = normalized * kriteria.bobot
            total_preferensi += preferensi
        
        hasil_perhitungan.append({
            'nasabah': nasabah,
            'nilai_akhir': total_preferensi,
            'matriks': semua_nilai[i],
            'normalisasi': row
        })
    
    return render_template('perhitungan_saw.html',
                         nasabahs=nasabahs,
                         kriterias=kriterias,
                         semua_nilai=semua_nilai,
                         matriks_normalisasi=matriks_normalisasi,
                         nilai_ideal=nilai_ideal,
                         hasil_perhitungan=hasil_perhitungan)

# ========== HASIL RANKING (HTML) ==========
@app.route('/ranking')
@login_required
def hasil_ranking():
    nasabahs = Nasabah.query.all()
    kriterias = Kriteria.query.order_by(Kriteria.kode).all()
    
    if not nasabahs:
        flash('Belum ada data nasabah!', 'warning')
        return redirect(url_for('dashboard'))
    
    # NILAI IDEAL
    nilai_ideal = {
        'C1': {'max': 90, 'min': 60},
        'C2': {'max': 85, 'min': 60},  
        'C3': {'max': 70, 'min': 50},
        'C4': {'max': 75, 'min': 55},
        'C5': {'max': 80, 'min': 60}
    }
    
    # Hitung ranking
    semua_nilai = []
    for nasabah in nasabahs:
        nilai_row = {'nasabah': nasabah}
        for kriteria in kriterias:
            nilai_nasabah = NilaiNasabah.query.filter_by(
                nasabah_id=nasabah.id,
                kriteria_id=kriteria.id
            ).first()
            nilai_row[kriteria.id] = nilai_nasabah.nilai if nilai_nasabah else 0
        semua_nilai.append(nilai_row)
    
    # Normalisasi dan hitung nilai preferensi
    hasil_perhitungan = []
    for row in semua_nilai:
        nasabah = row['nasabah']
        total_preferensi = 0
        
        for kriteria in kriterias:
            nilai = row[kriteria.id]
            ideal = nilai_ideal.get(kriteria.kode)
            
            if not ideal or nilai == 0:
                normalized = 0
            else:
                if kriteria.atribut == 'benefit':
                    max_val = ideal['max']
                    normalized = nilai / max_val if max_val > 0 else 0
                else:  # cost
                    min_val = ideal['min']
                    normalized = min_val / nilai if nilai > 0 else 0
            
            preferensi = normalized * kriteria.bobot
            total_preferensi += preferensi
        
        hasil_perhitungan.append({
            'nasabah': nasabah,
            'nilai_akhir': total_preferensi
        })
    
    # Urutkan dari nilai tertinggi ke terendah
    hasil_perhitungan.sort(key=lambda x: x['nilai_akhir'], reverse=True)
    
    return render_template('hasil_ranking.html',
                         hasil_perhitungan=hasil_perhitungan,
                         kriterias=kriterias)

# ========== LAPORAN ==========
@app.route('/laporan')
@login_required
def laporan():
    total_nasabah = Nasabah.query.count()
    return render_template('laporan.html', total_nasabah=total_nasabah)

# ========== API UNTUK VISUALISASI DIAGRAM ==========
@app.route('/api/ranking-visual')
@login_required
def ranking_visual():
    """API untuk data visualisasi ranking di dashboard"""
    nasabahs = Nasabah.query.all()
    kriterias = Kriteria.query.all()
    
    if not nasabahs:
        return jsonify({'error': 'Belum ada data nasabah'})
    
    # Nilai ideal VERSI BARU
    nilai_ideal = {
        'C1': 90, 'C2': 85, 'C3': 50, 'C4': 75, 'C5': 80
    }
    
    bobot = {
        'C1': 0.25, 'C2': 0.15, 'C3': 0.15, 'C4': 0.20, 'C5': 0.25
    }
    
    # Hitung skor setiap nasabah
    results = []
    for nasabah in nasabahs:
        total_score = 0
        
        for kriteria in kriterias:
            nilai_obj = NilaiNasabah.query.filter_by(
                nasabah_id=nasabah.id,
                kriteria_id=kriteria.id
            ).first()
            
            nilai = nilai_obj.nilai if nilai_obj else 0
            
            if nilai > 0:
                ideal = nilai_ideal.get(kriteria.kode, 1)
                
                if kriteria.atribut == 'benefit':
                    # Benefit: nilai / max
                    normalized = nilai / ideal
                else:  # cost (C3)
                    # Cost: min / nilai
                    normalized = ideal / nilai
                
                total_score += normalized * bobot.get(kriteria.kode, 0)
        
        # Konversi ke persen
        score_percent = min(total_score * 100, 100)
        
        # Tentukan kategori
        if score_percent >= 85:
            kategori = "Sangat Baik 🏆"
        elif score_percent >= 70:
            kategori = "Baik 👍"
        elif score_percent >= 55:
            kategori = "Cukup ✅"
        else:
            kategori = "Perlu Perbaikan ⚠️"
        
        results.append({
            'id': nasabah.id,
            'nama': nasabah.nama,
            'kode': nasabah.kode,
            'skor': round(score_percent, 1),
            'kategori': kategori
        })
    
    # Urutkan dari tertinggi
    results.sort(key=lambda x: x['skor'], reverse=True)
    
    return jsonify({
        'success': True,
        'data': results[:10],  # Ambil 10 teratas
        'total': len(results)
    })

@app.route('/api/laporan-data')
@login_required
def laporan_data():
    nasabahs = Nasabah.query.all()
    kriterias = Kriteria.query.order_by(Kriteria.kode).all()

    data = {
        'nasabahs': [],
        'kriterias': []
    }

    for kriteria in kriterias:
        data['kriterias'].append({
            'kode': kriteria.kode,
            'nama': kriteria.nama,
            'bobot': kriteria.bobot,
            'atribut': kriteria.atribut,
            'keterangan': kriteria.keterangan
        })

    for nasabah in nasabahs:
        nasabah_data = {
            'kode': nasabah.kode,
            'nama': nasabah.nama,
            'alamat': nasabah.alamat,
            'telepon': nasabah.telepon,
            'nilai': {}
        }

        for kriteria in kriterias:
            nilai_nasabah = NilaiNasabah.query.filter_by(
                nasabah_id=nasabah.id,
                kriteria_id=kriteria.id
            ).first()
            nasabah_data['nilai'][kriteria.kode] = nilai_nasabah.nilai if nilai_nasabah else 0

        data['nasabahs'].append(nasabah_data)

    return jsonify(data)

@app.route('/api/ranking')
@login_required
def api_ranking():
    return ranking_visual()

# ========== MANAJEMEN USER (OPSIONAL) ==========
@app.route('/users')
@login_required
def list_users():
    """List semua user (hanya admin)"""
    if current_user.role != 'admin':
        flash('Akses ditolak! Hanya admin yang dapat mengakses.', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/users/tambah', methods=['GET', 'POST'])
@login_required
def tambah_user():
    """Tambah user baru (hanya admin)"""
    if current_user.role != 'admin':
        flash('Akses ditolak! Hanya admin yang dapat menambah user.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        nama_lengkap = request.form.get('nama_lengkap', '').strip()
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        
        # Validasi
        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan!', 'danger')
            return redirect(url_for('tambah_user'))
        
        if len(password) < 6:
            flash('Password minimal 6 karakter!', 'danger')
            return redirect(url_for('tambah_user'))
        
        # Buat user baru
        user = User(
            username=username,
            nama_lengkap=nama_lengkap,
            role=role
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        flash(f'User {username} berhasil ditambahkan!', 'success')
        return redirect(url_for('list_users'))
    
    return render_template('user_form.html', action='Tambah')

@app.route('/users/hapus/<int:id>')
@login_required
def hapus_user(id):
    """Hapus user (hanya admin)"""
    if current_user.role != 'admin':
        flash('Akses ditolak! Hanya admin yang dapat menghapus user.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Tidak bisa hapus diri sendiri
    if id == current_user.id:
        flash('Tidak dapat menghapus akun sendiri!', 'danger')
        return redirect(url_for('list_users'))
    
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} berhasil dihapus!', 'success')
    return redirect(url_for('list_users'))

# ========== JALANKAN APLIKASI ==========
if __name__ == '__main__':
    with app.app_context():
        db.create_all()   # CUMA BUAT TABEL
    app.run(debug=True)
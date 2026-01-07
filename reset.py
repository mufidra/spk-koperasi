# reset.py
import os
from app import app, db
from models import User, Kriteria

with app.app_context():
    print("=" * 50)
    print("RESET DATABASE SPK KOPERASI")
    print("=" * 50)

    # Hapus database lama
    db_file = 'spk_koperasi.db'
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"🗑️  Database '{db_file}' dihapus")

    # Buat tabel baru
    print("\n📁 Membuat tabel database...")
    db.create_all()
    print("✅ Tabel berhasil dibuat")

    # Tambah admin
    print("\n👤 Menambahkan user admin...")
    admin = User(
        username='admin',
        nama_lengkap='Administrator Sistem',
        role='admin',
        active=True
    )
    admin.set_password('admin123')
    db.session.add(admin)

    # Tambah kriteria default
    print("\n📊 Menambahkan kriteria default...")
    kriteria_list = [
        {'kode':'C1','nama':'Besarnya Jumlah Pinjaman','atribut':'benefit','bobot':0.25,
         'keterangan':'>50jt:90\n21–50jt:80\n5–20jt:70\n≤5jt:60'},
        {'kode':'C2','nama':'Banyak Jumlah Tabungan','atribut':'benefit','bobot':0.15,
         'keterangan':'≥10jt:85\n5–9jt:70\n<5jt:60'},
        {'kode':'C3','nama':'Keaktifan','atribut':'cost','bobot':0.15,
         'keterangan':'Sering:70\nJarang:60\nTidak Pernah:50'},
        {'kode':'C4','nama':'Lama Keanggotaan','atribut':'benefit','bobot':0.20,
         'keterangan':'≥5 th:75\n3–4 th:65\n<3 th:55'},
        {'kode':'C5','nama':'Riwayat Tunggakan','atribut':'benefit','bobot':0.25,
         'keterangan':'Tidak:80\n1x:70\n≥2x:60'}
    ]

    for k in kriteria_list:
        db.session.add(Kriteria(**k))
        print(f"   ✓ {k['kode']}")

    db.session.commit()

    print("\n✅ DATABASE SIAP DIGUNAKAN")
    print("Login: admin / admin123")
    print("=" * 50)

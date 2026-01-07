from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from datetime import datetime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    nama_lengkap = db.Column(db.String(100))
    role = db.Column(db.String(20), default='admin')  # admin, user
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    # Flask-Login required methods
    def get_id(self):
        return str(self.id)
    
    @property
    def is_active_status(self):
        return self.active

class Nasabah(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode = db.Column(db.String(10), unique=True, nullable=False)
    nama = db.Column(db.String(100), nullable=False)
    alamat = db.Column(db.String(200))
    telepon = db.Column(db.String(15))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Nilai-nilai kriteria
    nilai = db.relationship('NilaiNasabah', backref='nasabah', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Nasabah {self.kode}>'

class Kriteria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode = db.Column(db.String(10), unique=True, nullable=False)
    nama = db.Column(db.String(100), nullable=False)
    atribut = db.Column(db.String(10), nullable=False)  # benefit/cost
    bobot = db.Column(db.Float, nullable=False)
    keterangan = db.Column(db.Text)  # Untuk menyimpan keterangan skor
    
    def __repr__(self):
        return f'<Kriteria {self.kode}>'

class NilaiNasabah(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nasabah_id = db.Column(db.Integer, db.ForeignKey('nasabah.id'), nullable=False)
    kriteria_id = db.Column(db.Integer, db.ForeignKey('kriteria.id'), nullable=False)
    nilai = db.Column(db.Float, nullable=False)
    
    # Relasi
    kriteria = db.relationship('Kriteria', backref='nilai_nasabah')
    
    __table_args__ = (db.UniqueConstraint('nasabah_id', 'kriteria_id', name='unique_nasabah_kriteria'),)
    
    def __repr__(self):
        return f'<NilaiNasabah {self.nasabah_id}-{self.kriteria_id}>'
# EventSync - Microservices Application

EventSync is a simple event management system built using a microservice architecture with Python and Flask. The system consists of two services:

1. **Event Service**: Manages events, venues, and available tickets.

- **Event Service** - Mengelola events, venue, dan ketersediaan tiket (port 5001)
- **Ticket Service** - Menangani reservasi dan pembelian tiket (port 5002)
- Setiap layanan memiliki database SQLite terpisah (`event_data.db` dan `ticket_data.db`)
- Komunikasi antar layanan menggunakan REST API

## Kebutuhan Sistem

- Python 3.8+
- Flask
- Flask-RESTful
- Flask-SQLAlchemy
- Requests

## Instalasi

1. Clone repository:
```bash
git clone <repository-url>
cd eventsync
```

2. Buat virtual environment:
```bash
python3 -m venv venv
```

3. Aktifkan virtual environment:
```bash
# Di Unix/Linux/Mac:
source venv/bin/activate

# Di Windows:
venv\Scripts\activate
```

4. Install dependensi:
```bash
pip install -r requirements.txt
```

## Menjalankan Aplikasi

### Menjalankan Kedua Service dalam Satu Terminal
Jalankan kedua service dalam terminal yang sama:
```bash
cd /Users/susantiafrilia/iaee/eventsync
source venv/bin/activate

# Jalankan Event Service di background
cd event_service
python app.py &

# Jalankan Ticket Service di foreground
cd ../ticket_service
python app.py
```

Dengan menggunakan `&` di akhir perintah pertama, Event Service akan berjalan di background sementara Ticket Service berjalan di foreground dalam terminal yang sama.

## Mengakses Tampilan Backend

Setelah kedua layanan berjalan, Anda dapat mengakses tampilan web melalui browser:

### Event Service (http://localhost:5001)
- **URL:** [http://localhost:5001](http://localhost:5001)
- **Fitur:**
  - Melihat daftar event dengan pencarian dan filter
  - Detail event dengan indikator ketersediaan tiket
  - Form pembuatan dan pengeditan event
  - Manajemen kapasitas dan harga tiket

### Ticket Service (http://localhost:5002)
- **URL:** [http://localhost:5002](http://localhost:5002)
  - Melihat daftar tiket dengan filter status
  - Form pembelian tiket dengan kalkulasi otomatis
  - Konfirmasi dan pembatalan reservasi
  - Manajemen status tiket (RESERVED, CONFIRMED, CANCELLED)

## Mengatasi Masalah Umum

### Port Sudah Digunakan
Jika Anda melihat error "Address already in use":

1. Ubah port di file `app.py` kedua layanan:
   ```python
   # Di event_service/app.py
   app.run(host='0.0.0.0', port=5003, debug=True)
   
   # Di ticket_service/app.py
   app.run(host='0.0.0.0', port=5004, debug=True)
   ```

2. Perbarui juga URL Event Service di Ticket Service:
   ```python
   # Di ticket_service/app.py
   EVENT_SERVICE_URL = os.getenv('EVENT_SERVICE_URL', 'http://localhost:5003')
   ```

### Error Database
Jika terjadi error skema database:
```bash
# Hapus database yang ada
rm /Users/susantiafrilia/iaee/eventsync/event_service/event_data.db
rm /Users/susantiafrilia/iaee/eventsync/ticket_service/ticket_data.db

# Jalankan kembali kedua layanan untuk membuat database baru
```

## Menggunakan Tampilan Web

### Event Service - Manajemen Event

1. **Halaman Utama Event**
   - Buka [http://localhost:5001](http://localhost:5001)
   - Anda akan melihat daftar semua event dengan kartu modern
   - Gunakan kotak pencarian untuk menemukan event tertentu
   - Kartu event menampilkan ketersediaan tiket dengan progress bar
   - Klik tombol "+ Create New Event" untuk membuat event baru

2. **Detail Event**
   - Klik "View Details" pada kartu event
   - Halaman detail menampilkan informasi lengkap event
   - Lihat status tiket tersedia dan progress penjualan
   - Tombol "Edit" dan "Delete" tersedia untuk manajemen

3. **Membuat/Mengedit Event**
   - Isi form dengan informasi yang diperlukan
   - Form memiliki validasi untuk memastikan data valid
   - Setelah mengirim, Anda akan diarahkan ke halaman detail event

### Ticket Service - Pembelian & Manajemen Tiket

1. **Halaman Utama Tiket**
   - Buka [http://localhost:5002](http://localhost:5002)
   - Lihat daftar semua tiket dengan status (RESERVED, CONFIRMED, CANCELLED)
   - Filter tiket berdasarkan status menggunakan dropdown
   - Klik tombol "Buy Ticket" untuk membeli tiket baru

2. **Pembelian Tiket**
   - Pilih event dari halaman detail event atau dari halaman Event Service
   - Isi form dengan nama, email, dan jumlah tiket
   - Harga akan dihitung otomatis berdasarkan jumlah tiket
   - Setelah mengirim, Anda akan diarahkan ke halaman detail tiket

3. **Detail & Manajemen Tiket**
   - Lihat informasi lengkap tiket dan event terkait
   - Tombol tindakan untuk mengkonfirmasi atau membatalkan reservasi
   - Status tiket ditampilkan dengan indikator visual jelas

## API Documentation

### Event Service (Port 5001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/events` | GET | Mendapatkan semua event |
| `/events/<id>` | GET | Mendapatkan event berdasarkan ID |
| `/events` | POST | Membuat event baru |
| `/events/<id>` | PUT | Memperbarui event |
| `/events/<id>` | DELETE | Menghapus event |
| `/events/<id>/tickets` | PUT | Memperbarui jumlah tiket tersedia |

### Ticket Service (Port 5002)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tickets` | GET | Mendapatkan semua tiket (dapat difilter berdasarkan event_id) |
| `/tickets/<id>` | GET | Mendapatkan tiket berdasarkan ID |
| `/tickets` | POST | Membuat reservasi tiket baru |
| `/tickets/<id>/status` | PUT | Memperbarui status tiket (konfirmasi/pembatalan) |
| `/tickets/<id>` | DELETE | Menghapus tiket |

## Contoh Penggunaan API

### 1. Membuat Event

```bash
curl -X POST http://localhost:5001/events \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Conference 2025",
    "description": "Annual technology conference",
    "event_date": "2025-06-15T09:00:00",
    "venue": "Convention Center",
    "total_tickets": 200
  }'
```

### 2. Memesan Tiket

```bash
curl -X POST http://localhost:5002/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": 1,
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "quantity": 2
  }'
```

### 3. Mengkonfirmasi Tiket

```bash
curl -X PUT http://localhost:5002/tickets/1/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "CONFIRMED"
  }'
```

### 4. Membatalkan Tiket

```bash
curl -X PUT http://localhost:5002/tickets/1/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "CANCELLED"
  }'
```


> **Catatan**: Untuk endpoints yang memerlukan request PUT/POST, Anda harus menggunakan curl atau aplikasi seperti Postman. Browser hanya mendukung request GET secara langsung.

## Integrasi Antar Layanan

Ticket Service berkomunikasi dengan Event Service untuk:
1. Memvalidasi event sebelum membuat tiket
2. Memeriksa ketersediaan tiket
3. Mereservasi atau melepaskan tiket saat status tiket berubah

Komunikasi sinkronus ini terjadi melalui REST API antar layanan.

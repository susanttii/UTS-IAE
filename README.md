# Event Service API Documentation

Event Service berperan untuk mengelola event dalam sistem EventSync.

## Peran Provider

Event Service bertindak sebagai provider melalui endpoint berikut:

### Daftar Semua Event
- **Endpoint**: `GET /events`
- **Deskripsi**: Menampilkan daftar semua event aktif
- **Response**: Array objek event
- **Contoh Response**:
```json
[
  {
    "id": 1,
    "judul": "Konser IndieFest",
    "lokasi": "Bandung",
    "tanggal": "2025-05-01"
  },
  {
    "id": 2,
    "judul": "Workshop AI",
    "lokasi": "Jakarta",
    "tanggal": "2025-05-05"
  }
]
```

### Detail Event
- **Endpoint**: `GET /event/{id}`
- **Deskripsi**: Mendapatkan detail event berdasarkan ID
- **Parameter**: `id` (path parameter)
- **Response**: Objek event tunggal
- **Contoh Response**:
```json
{
  "id": 2,
  "judul": "Workshop AI",
  "lokasi": "Jakarta",
  "tanggal": "2025-05-05"
}
```

### Membuat Event Baru
- **Endpoint**: `POST /event`
- **Deskripsi**: Membuat event baru
- **Request Body**: Objek event tanpa ID
- **Contoh Request**:
```json
{
  "judul": "Seminar Teknologi",
  "lokasi": "Surabaya",
  "tanggal": "2025-06-10"
}
```
- **Response**: Objek event yang telah dibuat beserta ID

### Memperbarui Event
- **Endpoint**: `PUT /event/{id}`
- **Deskripsi**: Memperbarui informasi event yang sudah ada
- **Parameter**: `id` (path parameter)
- **Request Body**: Objek event yang diperbarui
- **Response**: Objek event yang telah diperbarui

### Menghapus Event
- **Endpoint**: `DELETE /event/{id}`
- **Deskripsi**: Menghapus event
- **Parameter**: `id` (path parameter)
- **Response**: Pesan sukses

## Peran Consumer

Event Service mengkonsumsi data dari Ticket Service melalui endpoint berikut:

### Status Tiket Event
- **Endpoint**: `GET /tickets-status/{event_id}`
- **Deskripsi**: Mendapatkan status ketersediaan tiket untuk suatu event
- **Parameter**: `event_id` (path parameter)
- **Interaksi Consumer**: Membuat request ke endpoint Ticket Service `/tickets/{event_id}`
- **Response**: Objek status tiket
- **Contoh Response**:
```json
{
  "tersedia": 100,
  "dipesan": 50,
  "habis": false
}
```

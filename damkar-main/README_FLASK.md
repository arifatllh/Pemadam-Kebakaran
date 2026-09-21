# Damkar.Sub Flask Project

Project ini menjalankan tampilan website HTML/CSS Damkar menggunakan backend Flask Python.

## Struktur Folder

```text
damkar_flask_project/
├── app.py
├── requirements.txt
├── templates/
│   ├── landingPage.html
│   ├── detailLayanan.html
│   ├── detailEdukasi.html
│   ├── login.html
│   ├── dashboard.html
│   ├── DataLaporan.html
│   ├── TrackingLaporan.html
│   └── laporanKebakaran.html
└── static/
    ├── style.css
    ├── logo.png
    ├── favicon.png
    ├── user.png
    ├── clock.png
    ├── map.png
    └── assets/
        └── loginImg.webp
```

## Cara Menjalankan

1. Buka terminal di folder project.
2. Buat virtual environment:

```bash
python -m venv venv
```

3. Aktifkan virtual environment.

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

4. Install dependency:

```bash
pip install -r requirements.txt
```

5. Jalankan Flask:

```bash
python app.py
```

6. Buka browser:

```text
http://127.0.0.1:5000
```

## Route Halaman

- `/` diarahkan ke `landingPage.html`
- `/landingPage.html`
- `/detailLayanan.html`
- `/detailEdukasi.html`
- `/login.html`
- `/dashboard.html`
- `/DataLaporan.html`
- `/TrackingLaporan.html`
- `/laporanKebakaran.html`
- `/admin` diarahkan ke `dashboard.html`

## API Sederhana

Backend juga menyediakan API dasar:

- `GET /api/health`
- `GET /api/laporan`
- `POST /api/laporan`

Catatan: data laporan pada API masih disimpan sementara di memory. Jika server direstart, data akan hilang. Untuk versi produksi, gunakan database seperti SQLite/MySQL.

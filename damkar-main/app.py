from flask import Flask, render_template, redirect, url_for, jsonify, request, flash, session
from datetime import datetime
from uuid import uuid4
from pathlib import Path
from functools import wraps

import joblib
import pandas as pd


app = Flask(__name__)
app.secret_key = "damkar-sub-secret-key-change-me"


# =========================================================
# KONFIGURASI MODEL MACHINE LEARNING
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model_urgensi_damkar.joblib"

FEATURE_COLUMNS = [
    "skala_api",
    "korban_terjebak",
    "jumlah_korban",
    "jenis_bangunan",
    "kepadatan_lokasi",
]

urgency_model = None
model_load_error = None


def load_urgency_model():
    global model_load_error
    try:
        model = joblib.load(MODEL_PATH)
        return model
    except Exception as error:
        model_load_error = str(error)
        return None


urgency_model = load_urgency_model()


# =========================================================
# PENYIMPANAN SEMENTARA
# =========================================================

reports = []
pesan_kontak = []


# =========================================================
# HELPER LOGIN
# =========================================================

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# =========================================================
# HELPER MACHINE LEARNING
# =========================================================

def to_python_value(value):
    if hasattr(value, "item"):
        return value.item()
    return value


def normalize_report_features(data):
    missing = []
    for field in FEATURE_COLUMNS:
        value = data.get(field)
        if value is None or str(value).strip() == "":
            missing.append(field)

    if missing:
        return None, missing, "Field wajib belum lengkap"

    try:
        jumlah_korban = int(data.get("jumlah_korban", 0))
        if jumlah_korban < 0:
            return None, ["jumlah_korban"], "Jumlah korban tidak boleh kurang dari 0"
    except ValueError:
        return None, ["jumlah_korban"], "Jumlah korban harus berupa angka"

    korban_value = str(data.get("korban_terjebak")).strip().lower()

    # Dataset pakai "ya"/"tidak" (string), bukan 0/1
    if korban_value in ["1", "ya", "ada", "true"]:
        korban_terjebak = "ya"
    elif korban_value in ["0", "tidak", "tidak ada", "false"]:
        korban_terjebak = "tidak"
    else:
        return None, ["korban_terjebak"], "Nilai korban_terjebak harus 0/1 atau ada/tidak"

    features = {
        "skala_api": str(data.get("skala_api")).strip().lower(),
        "korban_terjebak": korban_terjebak,
        "jumlah_korban": jumlah_korban,
        "jenis_bangunan": str(data.get("jenis_bangunan")).strip().lower(),
        "kepadatan_lokasi": str(data.get("kepadatan_lokasi")).strip().lower(),
    }

    return features, [], None


def format_urgency_label(raw_prediction):
    raw_prediction = to_python_value(raw_prediction)
    if isinstance(raw_prediction, str):
        return raw_prediction
    label_map = {0: "Rendah", 1: "Sedang", 2: "Tinggi", 3: "Kritis"}
    try:
        return label_map.get(int(raw_prediction), str(raw_prediction))
    except Exception:
        return str(raw_prediction)


def status_from_urgency(urgency_label):
    label = str(urgency_label).lower()
    if "kritis" in label or "tinggi" in label:
        return "Prioritas Tinggi"
    if "sedang" in label:
        return "Prioritas Sedang"
    if "rendah" in label:
        return "Prioritas Normal"
    return "Menunggu Dispatch"


def predict_urgency(features):
    if urgency_model is None:
        return {
            "success": False,
            "message": "Model urgensi belum berhasil dimuat",
            "error": model_load_error,
        }

    input_df = pd.DataFrame([features], columns=FEATURE_COLUMNS)

    try:
        prediction = urgency_model.predict(input_df)
    except Exception as error:
        return {
            "success": False,
            "message": "Prediksi gagal. Format input tidak sesuai dengan model.",
            "error": str(error),
        }

    raw_prediction = to_python_value(prediction[0])
    urgency_label = format_urgency_label(raw_prediction)

    confidence = None
    if hasattr(urgency_model, "predict_proba"):
        try:
            probabilities = urgency_model.predict_proba(input_df)[0]
            confidence = round(float(max(probabilities)) * 100, 2)
        except Exception:
            confidence = None

    return {
        "success": True,
        "urgensi": urgency_label,
        "raw_prediction": raw_prediction,
        "confidence": confidence,
    }


# =========================================================
# ROUTE PUBLIK
# =========================================================

@app.route("/")
def index():
    return redirect(url_for("landing"))


@app.route("/landingPage")
def landing():
    return render_template("landingPage.html")


@app.route("/detailLayanan")
def detail_layanan():
    return render_template("detailLayanan.html")


@app.route("/detailEdukasi")
def detail_edukasi():
    return render_template("detailEdukasi.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == "admin" and password == "admin":
            session["logged_in"] = True
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Username atau password salah")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Anda berhasil logout", "success")
    return redirect(url_for("landing"))


# =========================================================
# FORM KONTAK LANDING
# =========================================================

@app.route("/kirim-pesan", methods=["POST"])
def kirim_pesan():
    data = request.form.to_dict()

    pesan = {
        "id": str(uuid4()),
        "nama": data.get("nama", "-"),
        "email": data.get("email", "-"),
        "telepon": data.get("telepon", "-"),
        "kategori": data.get("kategori", "-"),
        "subjek": data.get("subjek", "-"),
        "pesan": data.get("deskripsi", "-"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    pesan_kontak.append(pesan)

    flash("Pesan Anda sudah terkirim. Tim kami akan segera merespon.", "success")
    return redirect(url_for("landing") + "#kontak")


# =========================================================
# ROUTE ADMIN
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        reports=reports,
        pesan_kontak=pesan_kontak,
    )


@app.route("/DataLaporan")
@login_required
def data_laporan():
    detail_json = {}
    for r in reports:
        detail_json[r["id"]] = {
            "nama": r.get("nama", "-"),
            "email": r.get("email", "-"),
            "telepon": r.get("telepon", "-"),
            "status": r.get("status", "-"),
            "jenis": str(r.get("jenis_bangunan", "-")).replace("_", " ").title(),
            "regu": r.get("regu", "Belum ditugaskan"),
            "selesai": r.get("selesai", False),
            "alamat": r.get("lokasi", "-"),
            "kronologi": (
                f"Laporan dengan skala api {r.get('skala_api', '-')}, "
                f"{r.get('jumlah_korban', 0)} korban, "
                f"tingkat kepadatan {r.get('kepadatan_lokasi', '-')}. "
                f"Urgensi: {r.get('urgensi', '-')} "
                f"(confidence: {r.get('confidence', '-')}%)."
            ),
        }

    return render_template(
        "DataLaporan.html",
        reports=reports,
        detail_json=detail_json,
        pesan_kontak=pesan_kontak,
    )


@app.route("/TrackingLaporan")
@login_required
def tracking_laporan():
    report_id = request.args.get("id")
    report = None

    if report_id:
        report = next((r for r in reports if r["id"] == report_id), None)

    if report is None and reports:
        report = reports[-1]

    return render_template(
        "TrackingLaporan.html",
        report=report,
        pesan_kontak=pesan_kontak,
    )


# =========================================================
# LAPORAN KEBAKARAN — SELALU REDIRECT
# =========================================================

@app.route("/laporanKebakaran", methods=["GET", "POST"])
@login_required
def laporan_kebakaran():
    if request.method == "POST":
        data = request.form.to_dict()
        features, missing, error_message = normalize_report_features(data)

        # Validasi gagal → simpan di session, redirect balik
        if missing:
            session["form_error"] = error_message
            session["form_error_missing"] = missing
            session["form_data"] = data
            return redirect(url_for("laporan_kebakaran"))

        ml_result = predict_urgency(features)

        # ML gagal → simpan di session, redirect balik
        if not ml_result.get("success"):
            session["form_error"] = ml_result.get("message")
            session["form_data"] = data
            return redirect(url_for("laporan_kebakaran"))

        # Sukses → simpan laporan
        report = {
            "id": str(uuid4()),
            "nomor_laporan": f"FR-{datetime.now().strftime('%Y-%m-%d')}-{len(reports) + 1:06d}",
            "nama": data.get("nama", "-"),
            "email": data.get("email", "-"),
            "telepon": data.get("telepon", "-"),
            "lokasi": data.get("lokasi", "-"),
            "skala_api": features["skala_api"],
            "korban_terjebak": features["korban_terjebak"],
            "jumlah_korban": features["jumlah_korban"],
            "jenis_bangunan": features["jenis_bangunan"],
            "kepadatan_lokasi": features["kepadatan_lokasi"],
            "urgensi": ml_result["urgensi"],
            "confidence": ml_result["confidence"],
            "status": status_from_urgency(ml_result["urgensi"]),
            "regu": "-",
            "selesai": False,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

        reports.append(report)

        session.pop("form_error", None)
        session.pop("form_error_missing", None)
        session.pop("form_data", None)

        flash("Laporan berhasil disimpan", "success")
        return redirect(url_for("data_laporan"))

    # === GET — render form ===
    form_error = session.pop("form_error", None)
    form_error_missing = session.pop("form_error_missing", None)
    form_data = session.pop("form_data", None)

    return render_template(
        "laporanKebakaran.html",
        form_error=form_error,
        form_error_missing=form_error_missing,
        form_data=form_data,
        pesan_kontak=pesan_kontak,
    )


@app.route("/PesanKontak")
@login_required
def pesan_kontak_page():
    return render_template(
        "PesanKontak.html",
        pesan_list=pesan_kontak,
        pesan_kontak=pesan_kontak,
    )


# =========================================================
# ROUTE API
# =========================================================

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "message": "Backend Flask Damkar aktif",
        "model_loaded": urgency_model is not None,
        "model_file": MODEL_PATH.name,
        "model_error": model_load_error,
    })


@app.route("/api/stats")
def api_stats():
    total = len(reports)
    selesai = sum(1 for r in reports if r.get("selesai"))
    belum_selesai = total - selesai
    tinggi = sum(1 for r in reports if "Tinggi" in r.get("status", ""))
    regu_ditugaskan = sum(
        1 for r in reports
        if r.get("regu") and r.get("regu") != "-"
    )

    return jsonify({
        "success": True,
        "total": total,
        "selesai": selesai,
        "belum_selesai": belum_selesai,
        "prioritas_tinggi": tinggi,
        "regu_ditugaskan": regu_ditugaskan,
        "pesan_masuk": len(pesan_kontak),
    })


@app.route("/api/assign-regu", methods=["POST"])
@login_required
def assign_regu():
    data = request.get_json(silent=True) or request.form.to_dict()
    report_id = data.get("report_id")
    regu = data.get("regu")

    if not report_id or not regu:
        return jsonify({
            "success": False,
            "message": "report_id dan regu wajib diisi",
        }), 400

    target = next((r for r in reports if r["id"] == report_id), None)

    if not target:
        return jsonify({
            "success": False,
            "message": "Laporan tidak ditemukan",
        }), 404

    target["regu"] = regu

    return jsonify({
        "success": True,
        "message": f"Regu {regu} berhasil ditugaskan",
        "data": target,
    })


@app.route("/api/toggle-selesai", methods=["POST"])
@login_required
def toggle_selesai():
    data = request.get_json(silent=True) or request.form.to_dict()
    report_id = data.get("report_id")
    selesai = data.get("selesai")

    if report_id is None or selesai is None:
        return jsonify({
            "success": False,
            "message": "report_id dan selesai wajib diisi",
        }), 400

    target = next((r for r in reports if r["id"] == report_id), None)

    if not target:
        return jsonify({
            "success": False,
            "message": "Laporan tidak ditemukan",
        }), 404

    target["selesai"] = bool(selesai)

    return jsonify({
        "success": True,
        "message": "Status penyelesaian berhasil diperbarui",
        "data": target,
    })


@app.route("/api/predict-urgensi", methods=["POST"])
def predict_urgensi_api():
    data = request.get_json(silent=True) or request.form.to_dict()
    features, missing, error_message = normalize_report_features(data)

    if missing:
        return jsonify({
            "success": False,
            "message": error_message,
            "missing": missing,
        }), 400

    ml_result = predict_urgency(features)
    if not ml_result.get("success"):
        return jsonify(ml_result), 500

    return jsonify({
        "success": True,
        "input": features,
        "prediction": ml_result,
    })


@app.route("/api/laporan", methods=["GET", "POST"])
def laporan_api():
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict()
        has_ml_fields = any(field in data for field in FEATURE_COLUMNS)

        if has_ml_fields:
            features, missing, error_message = normalize_report_features(data)
            if missing:
                return jsonify({
                    "success": False,
                    "message": error_message,
                    "missing": missing,
                }), 400

            ml_result = predict_urgency(features)
            if not ml_result.get("success"):
                return jsonify(ml_result), 500

            report = {
                "id": str(uuid4()),
                "nomor_laporan": f"FR-{datetime.now().strftime('%Y-%m-%d')}-{len(reports) + 1:06d}",
                "nama": data.get("nama", "-"),
                "email": data.get("email", "-"),
                "telepon": data.get("telepon", "-"),
                "lokasi": data.get("lokasi", "-"),
                "skala_api": features["skala_api"],
                "korban_terjebak": features["korban_terjebak"],
                "jumlah_korban": features["jumlah_korban"],
                "jenis_bangunan": features["jenis_bangunan"],
                "kepadatan_lokasi": features["kepadatan_lokasi"],
                "urgensi": ml_result["urgensi"],
                "confidence": ml_result["confidence"],
                "status": status_from_urgency(ml_result["urgensi"]),
                "regu": "-",
                "selesai": False,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }

            reports.append(report)

            return jsonify({
                "success": True,
                "message": "Laporan berhasil disimpan",
                "data": report,
                "prediction": ml_result,
            }), 201

        required_fields = ["nama", "telepon", "lokasi", "jenis", "deskripsi"]
        missing = [f for f in required_fields if not str(data.get(f, "")).strip()]
        if missing:
            return jsonify({
                "success": False,
                "message": "Field wajib belum lengkap",
                "missing": missing,
            }), 400

        report = {
            "id": str(uuid4()),
            "nomor_laporan": f"FR-{datetime.now().strftime('%Y-%m-%d')}-{len(reports) + 1:06d}",
            "nama": data["nama"],
            "telepon": data["telepon"],
            "lokasi": data["lokasi"],
            "jenis": data["jenis"],
            "deskripsi": data["deskripsi"],
            "status": "Dalam Perjalanan",
            "regu": "-",
            "selesai": False,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

        reports.append(report)

        return jsonify({
            "success": True,
            "message": "Laporan berhasil disimpan",
            "data": report,
        }), 201

    return jsonify({"success": True, "data": reports})


@app.route("/api/pesan-kontak")
@login_required
def api_pesan_kontak():
    return jsonify({"success": True, "data": pesan_kontak})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
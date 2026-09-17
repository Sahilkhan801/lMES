from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import ocr_service
import compliance_checker
import pdf_generator
import os
import json
import uuid
import threading
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
DB_FILE = "scans_db.json"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
db_lock = threading.Lock()

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "LMES Compliance Engine", "timestamp": datetime.now().isoformat()}), 200

@app.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

def read_db():
    with db_lock:
        if not os.path.exists(DB_FILE):
            return []
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []

def write_db(data):
    with db_lock:
        temp_file = f"{DB_FILE}.tmp"
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, DB_FILE)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    image = request.files['image']
    if image.filename == '':
        return jsonify({"error": "No selected file"}), 400
    ext = os.path.splitext(image.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    image.save(filepath)
    ocr_result = ocr_service.extract_text(filepath, image.filename)
    if isinstance(ocr_result, dict):
        extracted_text = ocr_result.get("text", "")
        boxes = ocr_result.get("boxes", {})
        img_width = ocr_result.get("width", 0)
        img_height = ocr_result.get("height", 0)
    else:
        extracted_text = ocr_result
        boxes = {}
        img_width = 0
        img_height = 0
    report = compliance_checker.check(extracted_text)
    scan_id = str(uuid.uuid4().hex[:8])
    product_name = image.filename.replace("_", " ").replace("-", " ").split(".")[0].title()
    for keyword in ["chocolate_bar", "hair_oil", "smartwatch_box", "green_tea"]:
        if keyword in image.filename.lower():
            product_name = keyword.replace("_", " ").title()
    scan_record = {
        "id": scan_id,
        "product_name": product_name,
        "filename": filename,
        "original_filename": image.filename,
        "timestamp": datetime.now().isoformat(),
        "extracted_text": extracted_text,
        "compliance_score": report["compliance_score"],
        "overall_status": report["overall_status"],
        "results": report["results"],
        "issues": report["issues"],
        "boxes": boxes,
        "image_width": img_width,
        "image_height": img_height
    }
    db = read_db()
    db.append(scan_record)
    write_db(db)
    return jsonify(scan_record)

@app.route('/api/check_text', methods=['POST'])
def check_text():
    data = request.get_json()
    if not data or 'text' not in data or 'scan_id' not in data:
        return jsonify({"error": "Invalid request parameters"}), 400
    scan_id = data['scan_id']
    updated_text = data['text']
    product_name = data.get('product_name')
    db = read_db()
    record_index = -1
    for i, rec in enumerate(db):
        if rec['id'] == scan_id:
            record_index = i
            break
    if record_index == -1:
        return jsonify({"error": "Scan record not found"}), 404
    report = compliance_checker.check(updated_text)
    db[record_index]["extracted_text"] = updated_text
    db[record_index]["compliance_score"] = report["compliance_score"]
    db[record_index]["overall_status"] = report["overall_status"]
    db[record_index]["results"] = report["results"]
    db[record_index]["issues"] = report["issues"]
    if product_name:
        db[record_index]["product_name"] = product_name
    write_db(db)
    return jsonify(db[record_index])

@app.route('/api/history', methods=['GET'])
def get_history():
    db = read_db()
    db.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return jsonify(db)

@app.route('/api/history/<scan_id>', methods=['DELETE'])
def delete_history(scan_id):
    db = read_db()
    filtered_db = [rec for rec in db if rec['id'] != scan_id]
    if len(filtered_db) == len(db):
        return jsonify({"error": "Scan not found"}), 404
    write_db(filtered_db)
    return jsonify({"success": True, "message": "Scan deleted successfully"})

@app.route('/api/rules', methods=['GET', 'POST'])
def handle_rules():
    if request.method == 'GET':
        try:
            with open("rules.json", "r") as f:
                rules = json.load(f)
            return jsonify(rules)
        except Exception as e:
            return jsonify({"error": f"Failed to load rules: {str(e)}"}), 500
    else:
        try:
            new_rules = request.get_json()
            if not new_rules:
                return jsonify({"error": "Invalid JSON body"}), 400
            with open("rules.json", "w") as f:
                json.dump(new_rules, f, indent=2)
            return jsonify({"success": True, "message": "Rules updated successfully"})
        except Exception as e:
            return jsonify({"error": f"Failed to save rules: {str(e)}"}), 500

@app.route('/api/download_pdf/<scan_id>', methods=['GET'])
def download_pdf(scan_id):
    db = read_db()
    scan_record = None
    for rec in db:
        if rec['id'] == scan_id:
            scan_record = rec
            break
    if not scan_record:
        return "Scan record not found", 404
    try:
        pdf_bytes = pdf_generator.generate_pdf(scan_record, UPLOAD_FOLDER)
        from io import BytesIO
        pdf_file = BytesIO(pdf_bytes)
        safe_name = scan_record.get('product_name', 'compliance_report').replace(" ", "_").lower()
        return send_file(
            pdf_file,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"LM_Report_{safe_name}_{scan_id}.pdf"
        )
    except Exception as e:
        return f"Error generating PDF report: {str(e)}", 500

@app.route('/api/dashboard_stats', methods=['GET'])
def get_dashboard_stats():
    db = read_db()
    total_scans = len(db)
    if total_scans == 0:
        return jsonify({
            "total_scans": 0, "compliance_rate": 100, "violations_count": 0,
            "warnings_count": 0, "passed_count": 0, "violations_by_type": {},
            "compliance_by_category": {}, "recent_activity": []
        })
    passed_count = sum(1 for rec in db if rec.get("overall_status", "").upper() in ["PASSED", "PASS"])
    warning_count = sum(1 for rec in db if rec.get("overall_status", "").upper() in ["WARNING", "PARTIAL", "WARN"])
    failed_count = sum(1 for rec in db if rec.get("overall_status", "").upper() in ["FAILED", "FAIL"])
    compliance_rate = int((passed_count / total_scans) * 100)
    violations_by_type = {
        "MRP Format / Statement": 0, "Net Quantity Unit / Format": 0,
        "Mfg/Pkg Date Format": 0, "Manufacturer Name/Address": 0,
        "Consumer Care Details": 0, "Font Size Height": 0
    }
    key_mapping = {
        "MRP": "MRP Format / Statement", "mrp": "MRP Format / Statement",
        "NetQuantity": "Net Quantity Unit / Format", "net_quantity": "Net Quantity Unit / Format",
        "MfgDate": "Mfg/Pkg Date Format", "mfg_date": "Mfg/Pkg Date Format",
        "Manufacturer": "Manufacturer Name/Address", "manufacturer": "Manufacturer Name/Address",
        "ConsumerCare": "Consumer Care Details", "consumer_care": "Consumer Care Details",
        "FontSize": "Font Size Height", "font_size": "Font Size Height"
    }
    for rec in db:
        results = rec.get("results", {})
        for key, res in results.items():
            if res.get("status", "").upper() in ["FAILED", "FAIL", "WARNING"]:
                stat_key = key_mapping.get(key)
                if stat_key:
                    violations_by_type[stat_key] += 1
    categories = ["Food & Beverages", "Cosmetics & Personal Care", "Electronics", "Textiles / Others"]
    category_scans = {cat: [] for cat in categories}
    for rec in db:
        name = rec.get("product_name", "").lower()
        if any(x in name for x in ["chocolate", "tea", "flour", "food", "drink", "beverage", "organic"]):
            cat = "Food & Beverages"
        elif any(x in name for x in ["oil", "shampoo", "cream", "soap", "cosmetics", "hair"]):
            cat = "Cosmetics & Personal Care"
        elif any(x in name for x in ["watch", "smartwatch", "volt", "electronics", "phone", "device"]):
            cat = "Electronics"
        else:
            cat = "Textiles / Others"
        category_scans[cat].append(rec)
    compliance_by_category = {}
    for cat, list_scans in category_scans.items():
        if len(list_scans) == 0:
            compliance_by_category[cat] = 100
        else:
            cat_passed = sum(1 for rec in list_scans if rec.get("overall_status", "").upper() in ["PASSED", "PASS"])
            compliance_by_category[cat] = int((cat_passed / len(list_scans)) * 100)
    recent_activity = []
    sorted_scans = sorted(db, key=lambda x: x.get("timestamp", ""), reverse=True)
    for rec in sorted_scans[:5]:
        recent_activity.append({
            "id": rec.get("id"), "product_name": rec.get("product_name"),
            "overall_status": rec.get("overall_status"), "compliance_score": rec.get("compliance_score"),
            "timestamp": rec.get("timestamp")
        })
    return jsonify({
        "total_scans": total_scans, "compliance_rate": compliance_rate,
        "violations_count": failed_count, "warnings_count": warning_count,
        "passed_count": passed_count, "violations_by_type": violations_by_type,
        "compliance_by_category": compliance_by_category, "recent_activity": recent_activity
    })

@app.route('/analyze', methods=['POST'])
@app.route('/check_compliance', methods=['POST'])
def analyze_compliance_text():
    data = request.get_json() or {}
    if not data and request.form:
        data = request.form
    text = data.get("text") or data.get("extracted_text") or data.get("ocr_text") or ""
    font_size_val = data.get("physical_font_size") or data.get("font_size") or 2.0
    try:
        font_size = float(font_size_val)
    except (ValueError, TypeError):
        font_size = 2.0
    report = compliance_checker.check(text, font_size)
    return jsonify(report), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

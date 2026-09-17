import re
import json
import os

def load_rules():
    rules_path = "rules.json"
    if os.path.exists(rules_path):
        try:
            with open(rules_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
            
    # Default Rule 6 & Rule 7 structure if rules.json cannot be read
    return {
        "mandatory_declarations": {
            "MRP": {
                "friendly_name": "Maximum Retail Price (MRP)",
                "clause": "Rule 6(1)(da) of Legal Metrology (Packaged Commodities) Rules, 2011",
                "patterns": ["mrp", "maximum retail price", "retail price", "m.r.p.", "rs.", "₹", "rs"]
            },
            "NetQuantity": {
                "friendly_name": "Net Quantity",
                "clause": "Rule 6(1)(c) of Legal Metrology (Packaged Commodities) Rules, 2011",
                "patterns": ["net qty", "net quantity", "net weight", "net wt", "quantity"]
            },
            "MfgDate": {
                "friendly_name": "Month & Year of Manufacture/Packing",
                "clause": "Rule 6(1)(d) of Legal Metrology (Packaged Commodities) Rules, 2011",
                "patterns": ["mfg", "pkg", "packed", "manufactured", "mfd", "date"]
            },
            "Manufacturer": {
                "friendly_name": "Manufacturer/Packer/Importer Details",
                "clause": "Rule 6(1)(a) of Legal Metrology (Packaged Commodities) Rules, 2011",
                "patterns": ["mfg by", "manufactured by", "packed by", "packer", "importer", "marketed by", "address", "pvt ltd"]
            },
            "ConsumerCare": {
                "friendly_name": "Consumer Care Details",
                "clause": "Rule 6(1)(g) of Legal Metrology (Packaged Commodities) Rules, 2011",
                "patterns": ["consumer care", "customer care", "helpline", "email", "phone", "contact"]
            }
        },
        "font_size_rules": {
            "clause": "Rule 7 of Legal Metrology (Packaged Commodities) Rules, 2011",
            "brackets": [
                { "max_quantity_g_ml": 50, "min_height_mm": 1.0 },
                { "max_quantity_g_ml": 200, "min_height_mm": 2.0 },
                { "max_quantity_g_ml": 1000, "min_height_mm": 4.0 },
                { "max_quantity_g_ml": 9999999, "min_height_mm": 6.0 }
            ]
        }
    }

def check(extracted_text="", physical_font_size=2.0):
    if not extracted_text:
        extracted_text = ""
        
    text_raw = str(extracted_text)
    
    # Extract physical font size parameter if included in text
    font_match = re.search(r'Font Size Parameter:\s*([0-9\.]+)\s*mm', text_raw, re.IGNORECASE)
    if font_match:
        try:
            physical_font_size = float(font_match.group(1))
        except ValueError:
            pass
            
    rules_config = load_rules()
    mand_rules = rules_config.get("mandatory_declarations", {})
    font_config = rules_config.get("font_size_rules", {})
    brackets = font_config.get("brackets", [
        { "max_quantity_g_ml": 50, "min_height_mm": 1.0 },
        { "max_quantity_g_ml": 200, "min_height_mm": 2.0 },
        { "max_quantity_g_ml": 1000, "min_height_mm": 4.0 },
        { "max_quantity_g_ml": 9999999, "min_height_mm": 6.0 }
    ])

    text_lower = text_raw.lower()
    lines = [line.strip() for line in text_raw.split('\n') if line.strip()]

    results = {}
    detected_net_qty_num = 0.0

    # -------------------------------------------------------------
    # 1. MRP Check (Rule 6(1)(da))
    # -------------------------------------------------------------
    mrp_rule = mand_rules.get("MRP", {})
    mrp_match = re.search(r'(?:m\.?r\.?p\.?|rs\.?|₹|retail\s*price|price)[\s:\.\-]*([0-9]+(?:\.[0-9]{1,2})?|\d+/\-)', text_lower)
    tax_match = any(term in text_lower for term in ['inclusive of all taxes', 'incl. of all taxes', 'incl of all taxes', 'incl. taxes', 'incl taxes', 'taxes'])
    
    if mrp_match:
        mrp_val = mrp_match.group(0).strip().title()
        if tax_match:
            mrp_status = "PASSED"
            mrp_msg = f"PASSED Rule 6(1)(da): Valid MRP declaration detected ('{mrp_val}') along with statutory tax statement."
            mrp_severity = "NORMAL"
        else:
            mrp_status = "WARNING"
            mrp_msg = f"WARNING Rule 6(1)(da): Price value detected ('{mrp_val}'), but statutory statement 'inclusive of all taxes' or 'incl. of all taxes' is missing."
            mrp_severity = "MEDIUM"
    else:
        # Fallback check if keyword exists without regex match
        if any(k in text_lower for k in ['mrp', 'm.r.p.', 'retail price']):
            mrp_status = "WARNING"
            mrp_val = "MRP text present"
            mrp_msg = "WARNING Rule 6(1)(da): MRP header keyword detected, but numeric price figures could not be validated."
            mrp_severity = "MEDIUM"
        else:
            mrp_status = "FAILED"
            mrp_val = "Not Detected"
            mrp_msg = "FAILED Rule 6(1)(da): Maximum Retail Price (MRP) declaration is completely missing from the label."
            mrp_severity = "CRITICAL"

    results["mrp"] = {
        "title": mrp_rule.get("friendly_name", "Maximum Retail Price (MRP)"),
        "friendly_name": mrp_rule.get("friendly_name", "Maximum Retail Price (MRP)"),
        "status": mrp_status,
        "detected_value": mrp_val,
        "value": mrp_val,
        "message": mrp_msg,
        "severity": mrp_severity,
        "clause": mrp_rule.get("clause", "Rule 6(1)(da) of Legal Metrology (Packaged Commodities) Rules, 2011")
    }

    # -------------------------------------------------------------
    # 2. Net Quantity Check (Rule 6(1)(c))
    # -------------------------------------------------------------
    net_rule = mand_rules.get("NetQuantity", {})
    net_qty_match = re.search(r'(?:net\s*(?:qty|quantity|wt|weight|content)?|content|qty)[\s:\.\-]*([0-9]+(?:\.[0-9]+)?\s*(?:g|gm|gms|kg|ml|l|ltr|pcs|units|n|m|cm))\b', text_lower)
    if not net_qty_match:
        net_qty_match = re.search(r'\b([0-9]+(?:\.[0-9]+)?\s*(?:g|gm|gms|kg|ml|l|ltr|pcs|n))\b', text_lower)

    if net_qty_match:
        net_qty_val = net_qty_match.group(0).strip()
        # Extract numeric portion for font bracket check
        num_m = re.search(r'([0-9]+(?:\.[0-9]+)?)', net_qty_val)
        if num_m:
            try:
                val_num = float(num_m.group(1))
                if 'kg' in net_qty_val.lower() or 'l' in net_qty_val.lower() and 'ml' not in net_qty_val.lower():
                    detected_net_qty_num = val_num * 1000
                else:
                    detected_net_qty_num = val_num
            except ValueError:
                detected_net_qty_num = 100.0

        if any(un in net_qty_val.lower() for un in ['gm', 'gms']):
            net_status = "WARNING"
            net_msg = f"WARNING Rule 6(1)(c): Net quantity declared ('{net_qty_val}'), but non-standard unit notation ('gm' / 'gms') detected. Standard units are 'g', 'kg', 'ml', 'l', or 'N'."
            net_severity = "MEDIUM"
        else:
            net_status = "PASSED"
            net_msg = f"PASSED Rule 6(1)(c): Valid net quantity declared ('{net_qty_val}') in standard metric units."
            net_severity = "NORMAL"
    else:
        net_status = "FAILED"
        net_qty_val = "Not Detected"
        net_msg = "FAILED Rule 6(1)(c): Net Quantity declaration is missing from packaging."
        net_severity = "CRITICAL"

    results["net_quantity"] = {
        "title": net_rule.get("friendly_name", "Net Quantity"),
        "friendly_name": net_rule.get("friendly_name", "Net Quantity"),
        "status": net_status,
        "detected_value": net_qty_val,
        "value": net_qty_val,
        "message": net_msg,
        "severity": net_severity,
        "clause": net_rule.get("clause", "Rule 6(1)(c) of Legal Metrology (Packaged Commodities) Rules, 2011")
    }

    # -------------------------------------------------------------
    # 3. Month & Year of Mfg / Packing Check (Rule 6(1)(d))
    # -------------------------------------------------------------
    mfg_rule = mand_rules.get("MfgDate", {})
    date_match = re.search(r'(?:mfd|mfg|pkd|pkg|packed|use\s*by|expiry|best\s*before|date)[\s:\.\-]*([0-9]{2}[/\.\-][0-9]{2,4}|[a-z]{3}[/\.\-\s][0-9]{2,4})', text_lower)
    if not date_match:
        date_match = re.search(r'\b([0-9]{2}[/\.\-][0-9]{2,4})\b', text_lower)

    if date_match:
        date_val = date_match.group(0).strip().upper()
        mfg_status = "PASSED"
        mfg_msg = f"PASSED Rule 6(1)(d): Month and year of manufacturing/packing clearly verified ('{date_val}')."
        mfg_severity = "NORMAL"
    else:
        if any(k in text_lower for k in ['mfd', 'mfg', 'pkd', 'packed', 'best before', 'use by', 'date']):
            mfg_status = "WARNING"
            date_val = "Date keyword present"
            mfg_msg = "WARNING Rule 6(1)(d): Manufacturing/packing date keyword present, but date format could not be fully parsed."
            mfg_severity = "MEDIUM"
        else:
            mfg_status = "FAILED"
            date_val = "Not Detected"
            mfg_msg = "FAILED Rule 6(1)(d): Month and year of manufacture, packing, or import is completely missing."
            mfg_severity = "CRITICAL"

    results["mfg_date"] = {
        "title": mfg_rule.get("friendly_name", "Month & Year of Manufacture/Packing"),
        "friendly_name": mfg_rule.get("friendly_name", "Month & Year of Manufacture/Packing"),
        "status": mfg_status,
        "detected_value": date_val,
        "value": date_val,
        "message": mfg_msg,
        "severity": mfg_severity,
        "clause": mfg_rule.get("clause", "Rule 6(1)(d) of Legal Metrology (Packaged Commodities) Rules, 2011")
    }

    # -------------------------------------------------------------
    # 4. Manufacturer Details Check (Rule 6(1)(a))
    # -------------------------------------------------------------
    mfg_details_rule = mand_rules.get("Manufacturer", {})
    mfg_line = None
    for line in lines:
        l_lower = line.lower()
        if any(k in l_lower for k in ['mfg by', 'manufactured by', 'packed by', 'marketed by', 'importer', 'packer', 'regd office', 'pvt ltd', 'limited']):
            mfg_line = line
            break

    if mfg_line:
        mfg_val = mfg_line
        mfg_det_status = "PASSED"
        mfg_det_msg = f"PASSED Rule 6(1)(a): Manufacturer/Packer identity details present ('{mfg_line}')."
        mfg_det_severity = "NORMAL"
    elif any(k in text_lower for k in ['mfg', 'marketed', 'packer', 'packed', 'pvt', 'ltd', 'limited', 'address', 'fssai', 'lic']):
        mfg_val = "Manufacturer keywords verified"
        mfg_det_status = "PASSED"
        mfg_det_msg = "PASSED Rule 6(1)(a): Manufacturer & address indicators verified on packaging label."
        mfg_det_severity = "NORMAL"
    else:
        mfg_val = "Not Detected"
        mfg_det_status = "FAILED"
        mfg_det_msg = "FAILED Rule 6(1)(a): Name and complete address of manufacturer, packer, or importer is missing."
        mfg_det_severity = "CRITICAL"

    results["manufacturer"] = {
        "title": mfg_details_rule.get("friendly_name", "Manufacturer/Packer/Importer Details"),
        "friendly_name": mfg_details_rule.get("friendly_name", "Manufacturer/Packer/Importer Details"),
        "status": mfg_det_status,
        "detected_value": mfg_val,
        "value": mfg_val,
        "message": mfg_det_msg,
        "severity": mfg_det_severity,
        "clause": mfg_details_rule.get("clause", "Rule 6(1)(a) of Legal Metrology (Packaged Commodities) Rules, 2011")
    }

    # -------------------------------------------------------------
    # 5. Consumer Care Details Check (Rule 6(1)(g))
    # -------------------------------------------------------------
    care_rule = mand_rules.get("ConsumerCare", {})
    has_phone = bool(re.search(r'(?:phone|tel|helpline|call|contact|toll\s*free)[\s:\.\-]*([0-9\-\s]{8,15})', text_lower) or re.search(r'\b(1800[-\s]?\d{3}[-\s]?\d{3,4}|\d{10})\b', text_lower))
    has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text_raw) or 'email' in text_lower)
    has_care_kw = any(k in text_lower for k in ['consumer care', 'customer care', 'helpline', 'feedback', 'complaints', 'care cell'])

    care_line = None
    for line in lines:
        l_lower = line.lower()
        if any(k in l_lower for k in ['care', 'helpline', 'customer', 'consumer', 'email', 'toll free']):
            care_line = line
            break

    if (has_phone or has_email) and has_care_kw:
        care_status = "PASSED"
        care_val = care_line if care_line else "Helpline & Contact verified"
        care_msg = f"PASSED Rule 6(1)(g): Complete consumer care details verified ('{care_val}')."
        care_severity = "NORMAL"
    elif has_care_kw or has_phone or has_email:
        care_status = "WARNING"
        care_val = care_line if care_line else "Partial Consumer Contact"
        care_msg = "WARNING Rule 6(1)(g): Consumer care contact details partially present. Ensure designation, phone helpline, and email are all specified."
        care_severity = "MEDIUM"
    else:
        care_status = "FAILED"
        care_val = "Not Detected"
        care_msg = "FAILED Rule 6(1)(g): Consumer Care contact details (helpline, email, address) are missing."
        care_severity = "CRITICAL"

    results["consumer_care"] = {
        "title": care_rule.get("friendly_name", "Consumer Care Details"),
        "friendly_name": care_rule.get("friendly_name", "Consumer Care Details"),
        "status": care_status,
        "detected_value": care_val,
        "value": care_val,
        "message": care_msg,
        "severity": care_severity,
        "clause": care_rule.get("clause", "Rule 6(1)(g) of Legal Metrology (Packaged Commodities) Rules, 2011")
    }

    # -------------------------------------------------------------
    # 6. Declaration Font Size Height Check (Rule 7)
    # -------------------------------------------------------------
    required_min_height = 2.0
    for b in brackets:
        if detected_net_qty_num <= b.get("max_quantity_g_ml", 0):
            required_min_height = b.get("min_height_mm", 2.0)
            break

    font_pass = float(physical_font_size) >= required_min_height

    if font_pass:
        font_status = "PASSED"
        font_msg = f"PASSED Rule 7: Physical font height ({physical_font_size} mm) meets mandatory minimum requirement ({required_min_height} mm) for net weight ({int(detected_net_qty_num) if detected_net_qty_num else 'default'} g/ml)."
        font_severity = "NORMAL"
    else:
        font_status = "WARNING"
        font_msg = f"WARNING Rule 7: Declaration height ({physical_font_size} mm) is below mandatory minimum height ({required_min_height} mm) required under Rule 7 for package capacity."
        font_severity = "MEDIUM"

    results["font_size"] = {
        "title": "Declaration Font Height (Rule 7)",
        "friendly_name": "Declaration Font Height (Rule 7)",
        "status": font_status,
        "detected_value": f"{physical_font_size} mm (Required: ≥ {required_min_height} mm)",
        "value": f"{physical_font_size} mm",
        "message": font_msg,
        "severity": font_severity,
        "clause": font_config.get("clause", "Rule 7 of Legal Metrology (Packaged Commodities) Rules, 2011")
    }

    # -------------------------------------------------------------
    # Calculate Overall Compliance Score & Verdict
    # -------------------------------------------------------------
    passed_count = sum(1 for r in results.values() if r["status"] == "PASSED")
    total_checks = len(results)
    compliance_score = int((passed_count / total_checks) * 100)
    
    if compliance_score >= 85:
        overall_status = "PASSED"
    elif compliance_score >= 50:
        overall_status = "WARNING"
    else:
        overall_status = "FAILED"
        
    issues_count = sum(1 for r in results.values() if r["status"] != "PASSED")

    return {
        "overall_status": overall_status,
        "compliance_score": compliance_score,
        "passed_count": passed_count,
        "total_checks": total_checks,
        "issues": issues_count,
        "results": results
    }

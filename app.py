from flask import Flask, render_template, request, redirect, url_for, session
import os
import requests
import pandas as pd
from typing import List, Dict

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management

@app.route("/", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        # Capture configuration from the user
        session["access_token"] = request.form["access_token"]
        session["phone_number_id"] = request.form["phone_number_id"]
        session["whatsapp_business_id"] = request.form["whatsapp_business_id"]
        return redirect(url_for("index"))

    # Render the configuration page
    return render_template(
        "config.html",
        access_token=session.get("access_token", ""),
        phone_number_id=session.get("phone_number_id", ""),
        whatsapp_business_id=session.get("whatsapp_business_id", "")
    )

@app.route("/index", methods=["GET", "POST"])
def index():
    if not all(key in session for key in ["access_token", "phone_number_id", "whatsapp_business_id"]):
        return redirect(url_for("config"))

    access_token = session["access_token"]
    phone_number_id = session["phone_number_id"]
    whatsapp_business_id = session["whatsapp_business_id"]

    # Fetch available templates
    templates = fetch_templates(access_token, whatsapp_business_id)

    if request.method == "POST":
        selected_template = request.form["template"]
        csv_file = request.files["csv_file"]

        results = []
        try:
            # Read CSV file
            data = pd.read_csv(csv_file, dtype=str)

            # Get template details
            template_details = next((t for t in templates if t["name"] == selected_template), None)
            required_params = template_details.get("param_count", 0)

            # Process each row in the CSV
            for _, row in data.iterrows():
                phone_number = row.get("phone_number")
                params = [
                    {"type": "text", "text": row.get(f"param_{i+1}", "")}
                    for i in range(required_params)
                ]

                # Send message
                response = send_message(access_token, phone_number_id, phone_number, selected_template, params)
                if response.status_code == 200:
                    results.append({"phone_number": phone_number, "status": "success"})
                else:
                    error_message = response.json().get("error", {}).get("message", "Unknown error")
                    results.append({"phone_number": phone_number, "status": "failure", "error": error_message})

            return render_template("index.html", templates=templates, results=results)

        except Exception as e:
            return render_template("index.html", templates=templates, error=str(e))

    return render_template("index.html", templates=templates)

def fetch_templates(access_token: str, whatsapp_business_id: str) -> List[Dict]:
    """Fetch templates from the WhatsApp API."""
    url = f"https://graph.facebook.com/v21.0/{whatsapp_business_id}/message_templates"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        templates = response.json().get("data", [])
        for template in templates:
            components = template.get("components", [])
            body_component = next((c for c in components if c.get("type") == "BODY"), {})
            body_text = body_component.get("text", "")

            # Count placeholders in body text
            template["param_count"] = body_text.count("{{")
            template["body_text"] = body_text or "No content available"

        return templates

    return []

def send_message(access_token: str, phone_number_id: str, phone_number: str, template_name: str, params: List[Dict]) -> requests.Response:
    """Send a message using the WhatsApp API."""
    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": [
                {"type": "body", "parameters": params}
            ],
        },
    }
    response = requests.post(url, headers=headers, json=payload)
    return response

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import requests
import pandas as pd
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management


@app.route("/", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        # Capture configuration from the user
        session["access_token"] = request.form["access_token"]
        session["phone_number_id"] = request.form["phone_number_id"]
        session["whatsapp_business_id"] = request.form["whatsapp_business_id"]

        # Redirect to index after saving the data
        return redirect(url_for("index"))

    # Render the configuration page
    return render_template("config.html", 
                           access_token=session.get("access_token", ""), 
                           phone_number_id=session.get("phone_number_id", ""),
                           whatsapp_business_id=session.get("whatsapp_business_id", ""))

# Route for index page
@app.route("/index", methods=["GET", "POST"])
def index():
    if "access_token" not in session or "phone_number_id" not in session or "whatsapp_business_id" not in session:
        return redirect(url_for("config"))

    access_token = session["access_token"]
    phone_number_id = session["phone_number_id"]
    whatsapp_business_id = session["whatsapp_business_id"]

    # Fetch available templates
    templates = fetch_templates(access_token, whatsapp_business_id)

    if request.method == "POST":
        selected_template = request.form["template"]
        csv_file = request.files["csv_file"]

        try:
            # Read CSV file
            data = pd.read_csv(csv_file, dtype=str)

            # Get template details
            template_details = next(
                (t for t in templates if t["name"] == selected_template), None
            )
            required_params = template_details["param_count"]

            # Validate parameters if required
            if required_params > 0:
                if required_params > len(data.columns) - 1:
                    return render_template(
                        "index.html",
                        templates=templates,
                        error=f"Template requires {required_params} parameters, but your CSV has fewer columns!",
                    )

                # Map CSV data to parameters
                errors = []
                for _, row in data.iterrows():
                    phone_number = row["phone_number"]
                    params = [{"type": "text", "text": row[f"param_{i+1}"]} for i in range(required_params)]

                    # Send message
                    response = send_message(access_token, phone_number_id, phone_number, selected_template, params)
                    if response.status_code != 200:
                        errors.append({"phone_number": phone_number, "error": response.json()})
            else:
                # For templates with no parameters
                errors = []
                for _, row in data.iterrows():
                    phone_number = row["phone_number"]
                    response = send_message(access_token, phone_number_id, phone_number, selected_template, [])
                    if response.status_code != 200:
                        errors.append({"phone_number": phone_number, "error": response.json()})

            return render_template("index.html", templates=templates, success="Messages sent!", errors=errors)

        except Exception as e:
            return render_template("index.html", templates=templates, error=str(e))

    return render_template("index.html", templates=templates)


# Fetch templates from WhatsApp API
# Fetch templates from WhatsApp API
def fetch_templates(access_token, whatsapp_business_id):
    url = f"https://graph.facebook.com/v21.0/{whatsapp_business_id}/message_templates"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        templates = response.json().get("data", [])
        
        for template in templates:
            components = template.get("components", [])
            if components:
                # Find the body component
                body_component = next((c for c in components if c["type"] == "BODY"), {})
                body_text = body_component.get("text", "")
                
                # Count the placeholders (e.g., {{1}}, {{2}}, ...)
                template["param_count"] = body_text.count("{{")
                template["body_text"] = body_text  # Include body text for preview
            else:
                template["param_count"] = 0  # Default to 0 if no body component found
                template["body_text"] = "No content available"
        
        return templates

    return []




# Send a message using the WhatsApp API
def send_message(access_token, phone_number_id, phone_number, template_name, params):
    print(params)
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
                {"type": "body", 
                 "parameters": params
                 }],
        },
    }
    response = requests.post(url, headers=headers, json=payload)
    print(response.json())  # Debugging - View API response
    return response

if __name__ == "__main__":
    app.run(debug=True)

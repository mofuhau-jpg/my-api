# app.py
from flask import Flask, request, jsonify
from log import generate_reference

app = Flask(__name__)

@app.route("/api/reference", methods=["POST"])
def reference():
    data = request.get_json()
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    result = generate_reference(url)
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)

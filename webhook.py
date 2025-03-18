from flask import Flask, request, jsonify
import json
import base64

app = Flask(__name__)

DOCKERHUB_SECRET_NAME = "dockerhub-secret"

@app.route("/mutate", methods=["POST"])
def mutate():
    req = request.get_json()
    uid = req["request"]["uid"]
    service_account = req["request"]["object"]

    # Ensure 'imagePullSecrets' exists
    if "imagePullSecrets" not in service_account:
        service_account["imagePullSecrets"] = []

    # Add 'dockerhub-secret' if not already present
    if not any(secret["name"] == DOCKERHUB_SECRET_NAME for secret in service_account["imagePullSecrets"]):
        service_account["imagePullSecrets"].append({"name": DOCKERHUB_SECRET_NAME})

    # Create JSON Patch
    patch = [{"op": "add", "path": "/imagePullSecrets/-", "value": {"name": DOCKERHUB_SECRET_NAME}}]
    patch_b64 = base64.b64encode(json.dumps(patch).encode()).decode()

    return jsonify({
        "response": {
            "uid": uid,
            "allowed": True,
            "patchType": "JSONPatch",
            "patch": patch_b64
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=443, ssl_context=("/certs/tls.crt", "/certs/tls.key"))
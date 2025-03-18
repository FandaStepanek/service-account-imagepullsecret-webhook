from flask import Flask, request, jsonify
import json
import base64

app = Flask(__name__)

DOCKERHUB_SECRET_NAME = "dockerhub-secret"

@app.route("/mutate", methods=["POST"])
def mutate():
    req = request.get_json()
    
    if "request" not in req:
        return jsonify({"error": "Invalid AdmissionReview request"}), 400

    uid = req["request"]["uid"]
    service_account = req["request"]["object"]

    # Ensure 'imagePullSecrets' exists
    patches = []
    if "imagePullSecrets" not in service_account:
        patches.append({"op": "add", "path": "/imagePullSecrets", "value": []})

    # Add 'dockerhub-secret' if not already present
    if not any(secret["name"] == DOCKERHUB_SECRET_NAME for secret in service_account.get("imagePullSecrets", [])):
        patches.append({"op": "add", "path": "/imagePullSecrets/-", "value": {"name": DOCKERHUB_SECRET_NAME}})

    patch_b64 = base64.b64encode(json.dumps(patches).encode()).decode()

    response = {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": {
            "uid": uid,
            "allowed": True,
            "patchType": "JSONPatch",
            "patch": patch_b64
        }
    }

    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=443, ssl_context=("/certs/tls.crt", "/certs/tls.key"))

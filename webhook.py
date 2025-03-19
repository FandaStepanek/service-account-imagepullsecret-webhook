from flask import Flask, request, jsonify
import json
import base64
import os
import requests
import logging

app = Flask(__name__)
app.logger.setLevel(logging.INFO) 

# Kubernetes API Config
K8S_API_SERVER = os.getenv("K8S_API_SERVER", "https://kubernetes.default.svc")
K8S_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
K8S_CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

# Secret Config
DOCKERHUB_SECRET_NAME = "dockerhub-secret"
DEFAULT_NAMESPACE = os.getenv("DEFAULT_NAMESPACE", "default")

def get_k8s_token():
    """ Reads Kubernetes service account token for API authentication """
    with open(K8S_TOKEN_PATH, "r") as file:
        return file.read().strip()

def check_secret_exists(namespace):
    """ Checks if the `dockerhub-secret` exists in the given namespace """
    url = f"{K8S_API_SERVER}/api/v1/namespaces/{namespace}/secrets/{DOCKERHUB_SECRET_NAME}"
    headers = {"Authorization": f"Bearer {get_k8s_token()}"}

    response = requests.get(url, headers=headers, verify=K8S_CA_PATH)
    app.logger.info(f"Response code: {response.status_code}")
    app.logger.info(f"Response text: {response.text}")
    return response.status_code == 200  # Returns True if secret exists

def copy_secret_to_namespace(namespace):
    """ Copies the `dockerhub-secret` from `default` namespace to the target namespace """
    # Get secret from default namespace
    url_get = f"{K8S_API_SERVER}/api/v1/namespaces/{DEFAULT_NAMESPACE}/secrets/{DOCKERHUB_SECRET_NAME}"
    url_create = f"{K8S_API_SERVER}/api/v1/namespaces/{namespace}/secrets"
    token = get_k8s_token()
    app.logger.info(f"Using token: {token}")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url_get, headers=headers, verify=K8S_CA_PATH)
    
    app.logger.info(f"Response code: {response.status_code}")
    app.logger.info(f"Response text: {response.text}")
    if response.status_code != 200:
        app.logger.info(f" ERROR: Failed to get `{DOCKERHUB_SECRET_NAME}` from `{DEFAULT_NAMESPACE}`")
        return False
    
    secret_data = response.json()
    
    # Modify the secret metadata for the new namespace
    secret_data["metadata"].pop("uid", None)
    secret_data["metadata"].pop("resourceVersion", None)
    secret_data["metadata"]["namespace"] = namespace

    response = requests.post(url_create, headers=headers, json=secret_data, verify=K8S_CA_PATH)
    
    if response.status_code == 201:
        app.logger.info(f" Copied `{DOCKERHUB_SECRET_NAME}` to `{namespace}`")
        return True
    else:
        app.logger.error(f" ERROR: Failed to create `{DOCKERHUB_SECRET_NAME}` in `{namespace}`: {response.text}")
        return False

@app.route("/mutate", methods=["POST"])
def mutate():
    req = request.get_json()
    
    if "request" not in req:
        return jsonify({"error": "Invalid AdmissionReview request"}), 400
    
    uid = req["request"]["uid"]
    object_kind = req["request"]["kind"]["kind"]

    if object_kind == "ServiceAccount":
        namespace = req["request"]["namespace"]
        service_account = req["request"]["object"]
        patches = []

        # Ensure `dockerhub-secret` exists in the namespace
        app.logger.info(f"Inspecting namespace: {namespace}")
        if not check_secret_exists(namespace):
            copy_secret_to_namespace(namespace)

        # Patch ServiceAccount with `dockerhub-secret`
        if "imagePullSecrets" not in service_account:
            patches.append({"op": "add", "path": "/imagePullSecrets", "value": []})

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

    return jsonify({"error": "Unhandled request"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8124, ssl_context=("/certs/tls.crt", "/certs/tls.key"))

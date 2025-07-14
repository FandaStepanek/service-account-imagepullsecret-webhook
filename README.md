# 🔐 Service Account ImagePullSecret Webhook

This Kubernetes [mutating admission webhook](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/) automatically adds a pre-configured `imagePullSecret` to all newly created `ServiceAccounts`. This ensures that pods using these service accounts can authenticate to Docker Hub (or other registries) without manual intervention.


## 🎯 Purpose

- Injects a Docker Hub pull secret (or other private registry credentials) into each new `ServiceAccount`.
- Ensures consistent and seamless image pulling across all namespaces (cluster-scoped).


## ⚙️ How It Works

- Listens for `CREATE` operations on `ServiceAccount` resources.
- If the service account does not already include the configured secret, the webhook mutates the resource to include it.
- Runs as a Kubernetes deployment with a corresponding `MutatingWebhookConfiguration`.


## Publish
`docker buildx build --platform linux/amd64,linux/arm64 -t ghcr.io/fandastepanek/service-account-webhook:latest --push .`

# CloudPulse — Interview Preparation & Architecture Guide

This guide is designed to prepare you for technical interviews. It explains the design decisions, tools, and workflows of **CloudPulse** so you can confidently walk interviewers through it.

---

## 1. System Architecture

```
                                 +------------------------+
                                 |  Developer Local Env   |
                                 +-----------+------------+
                                             | git push
                                             v
                                 +------------------------+
                                 |   GitHub Repository    |
                                 +-----------+------------+
                                             | triggers
                                             v
                                 +------------------------+
                                 |  GitHub Actions (CI)   |
                                 +-----------+------------+
                                 | 1. Run Flake8 / Pytest |
                                 | 2. Build Docker Image  |
                                 | 3. Push to Docker Hub  |
                                 | 4. Update image tag    |
                                 |    in values-env.yaml  |
                                 +-----------+------------+
                                             | git commit & push
                                             v
                                 +------------------------+
                                 |   GitHub Repo Config   |
                                 +-----------+------------+
                                             ^
                                             | poll / webhook
                                             v
+--------------------------------------------+--------------------------------------------+
| Kubernetes Cluster                                                                      |
|                                                                                         |
|      +---------------------+                                                            |
|      |    ArgoCD Agent     | <==================================================+       |
|      +----------+----------+                                                            |       |
|                 | syncs changes                                                         |       |
|                 v                                                                       |       |
|      +-------------------------------------------------------------------------------+  |       |
|      | Namespaces                                                                    |  |       |
|      |                                                                               |  |       |
|      |   [ staging ]                               [ production ]                    |  |       |
|      |   - Pods (FastAPI API)                      - Pods (FastAPI API)              |  |       |
|      |   - Services / Ingresses                    - Services / Ingresses            |  |       |
|      |   - ConfigMaps / Secrets                    - ConfigMaps / Secrets            |  |       |
|      +-------------------------------------------------------------------------------+  |       |
|                 | scrapes /metrics                                                      |       |
|                 v                                                                       |       |
|      +---------------------+                                                            |       |
|      | Prometheus Server   |                                                            |       |
|      +----------+----------+                                                            |       |
|                 | queries                                                               |       |
|                 v                                                                       |       |
|      +---------------------+                                                            |       |
|      |  Grafana Dashboard  |                                                            |       |
|      +---------------------+                                                            |       |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Core DevOps Concepts in CloudPulse

### A. Infrastructure as Code (IaC) with Terraform
* **What it does**: Provisions the underlying servers/infrastructure (like a DigitalOcean VM or AWS EKS cluster) automatically using configuration files (`main.tf`).
* **Why it's used**: Instead of manually logging into a cloud console and clicking buttons (which is error-prone and hard to replicate), Terraform lets us define the infrastructure in code. If our cluster crashes, we can run `terraform apply` to spin up a new, identical one in seconds.

### B. Containerization with Docker
* **What it does**: Packages the FastAPI application and its dependencies (Python, packages) into a lightweight, standalone container image.
* **Why it's used**: Solves the "works on my machine" problem. The exact same container image runs in your local development environment, the staging environment, and the production environment.
* **Security & Optimization**:
  - **Multi-stage builds** are recommended (keeps the final image size small by leaving out build dependencies).
  - **Rootless user (`appuser`)**: The container runs under a non-privileged user instead of `root`, preventing container escape vulnerabilities.

### C. GitOps & ArgoCD
* **What it does**: ArgoCD sits inside the Kubernetes cluster and continuously monitors the GitHub repository. When Git updates, ArgoCD automatically adjusts the Kubernetes cluster resources to match.
* **Why it's used**: Traditional CI/CD "pushes" deployments directly to clusters (requiring GitHub Actions to have full admin SSH keys/secrets). ArgoCD uses a "pull" model, where the cluster pulls its state from Git. This keeps secrets secure inside the cluster and guarantees that Git remains the single source of truth.

### D. Helm (Kubernetes Package Manager)
* **What it does**: Bundles all our Kubernetes manifests (Deployments, Services, ConfigMaps) into a template package called a Chart.
* **Why it's used**: Instead of duplicating YAML files for staging and production, we write templates once, and use `values-staging.yaml` and `values-production.yaml` to fill in environment-specific configuration (like replica count, database URLs, and resource constraints).

### E. Observability with Prometheus & Grafana
* **What it does**: Prometheus scrapes raw numerical metrics from our FastAPI app's `/metrics` endpoint. Grafana queries Prometheus and displays these metrics on a visual dashboard.
* **Why it's used**: In production, you need to know *before* users do if your app is crashing, running out of memory, or serving slow requests.

---

## 3. High-Value Interview Q&As

### Q1: "Why did you choose GitOps/ArgoCD instead of just having GitHub Actions deploy directly?"
* **Answer**: *"I chose GitOps with ArgoCD for security and configuration consistency. In a traditional push model, the CI tool (GitHub Actions) requires admin-level access credentials to the Kubernetes cluster, creating a massive security risk if the CI pipeline is compromised. In contrast, ArgoCD runs natively inside the cluster and pulls configuration changes from Git. Furthermore, ArgoCD constantly monitors the cluster for 'configuration drift.' If an engineer manually alters a service in the cluster via `kubectl`, ArgoCD immediately detects that it doesn't match the Git repository and reverts the changes automatically, enforcing Git as the absolute source of truth."*

### Q2: "How does the self-healing and auto-recovery mechanism work in this project?"
* **Answer**: *"Self-healing is implemented at both the Kubernetes level and the application level. 
  1. In the `Dockerfile` and the deployment manifests, I configured **Liveness** and **Readiness probes**.
  2. The **Readiness probe** hits the `/health` endpoint to verify that the app is ready to accept traffic. If the endpoint doesn't respond (e.g. because the database connection is failing), Kubernetes stops sending traffic to that pod.
  3. The **Liveness probe** continuously monitors the health of the container. If the app locks up or enters an infinite loop, the liveness probe fails, and Kubernetes kills the unhealthy pod and starts a fresh one.
  4. ArgoCD also has **SelfHeal** enabled. If any manifest in the cluster is deleted or edited out-of-sync with Git, ArgoCD redeploys it immediately."*

### Q3: "How are database credentials and secrets handled in this architecture? How would you do it in production?"
* **Answer**: *"Currently, Kubernetes `Secrets` are referenced dynamically. For a local setup, they are configured via environment variables and ConfigMaps. For a production pipeline, I wouldn't commit raw secrets to GitHub. I would use a secure secrets manager. The two industry standards are:
  1. **Sealed Secrets (Bitnami)**: Where secrets are encrypted using a public key and can be safely committed to Git, but only decrypted by the controller inside the cluster.
  2. **HashiCorp Vault or AWS Secrets Manager** integrated with **External Secrets Operator (ESO)** in Kubernetes, which pulls secrets directly from the cloud provider at runtime."*

### Q4: "Why did you use Helm instead of Kustomize or plain YAML templates?"
* **Answer**: *"Plain YAML templates lead to duplicate configurations and copy-paste errors across staging and production environments. I chose Helm because it allows us to parameterize our manifests. We have one base template, and we manage environmental differences via value override files (`values-staging.yaml` and `values-production.yaml`). This makes it simple to scale up production replicas (e.g., to 3 replicas with high resource allocations) while keeping staging lightweight (1 replica, low resources) without duplicating manifest declarations."*

### Q5: "What happens if a new deployment is pushed, but it has a bug and crashes immediately? How does the system roll back?"
* **Answer**: *"When a new image tag is committed to Git, ArgoCD attempts to sync the cluster. 
  1. It performs a **rolling update**, spinning up new pods alongside the old ones.
  2. The new pods fail their **readiness probe** because they are crashing.
  3. Since the new pods never become ready, Kubernetes refuse to direct traffic to them and will not terminate the old, healthy pods. 
  4. To roll back fully, ArgoCD can be configured to auto-rollback when a sync fails, or we can simply revert the commit in Git. Because Git is the single source of truth, reverting the commit triggers the CI/CD pipeline to revert the image tag, and ArgoCD immediately syncs back to the last stable state."*

---

## 4. Key CLI Commands for Quick Review

Keep these commands fresh in your head so you can explain how you inspect the cluster:

* **Inspect pod statuses and restarts (useful for checking crash loops)**:
  ```bash
  kubectl get pods -n staging
  ```
* **Read live logs of the FastAPI app**:
  ```bash
  kubectl logs -l app.kubernetes.io/name=cloudpulse -n staging --tail=50 -f
  ```
* **Verify configuration drift or sync status in ArgoCD**:
  ```bash
  argocd app get cloudpulse-staging
  ```
* **Dry-run/Render Helm templates locally (verifies YAML is correct before pushing)**:
  ```bash
  helm template cloudpulse ./helm-chart/cloudpulse
  ```
* **Inspect resource usage of pods (useful for sizing CPU/Memory limits)**:
  ```bash
  kubectl top pods -n staging
  ```

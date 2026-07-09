# CloudPulse — Kubernetes GitOps Deployment Platform

A FastAPI microservice deployed through a full GitOps pipeline: GitHub Actions
builds and tests the code, Helm packages it for Kubernetes, and ArgoCD
automatically syncs staging/production environments to match what's in Git —
with health-check-based self-healing.

## Architecture

```
Push to GitHub
      |
      v
GitHub Actions (test -> build image -> push to Docker Hub -> update Helm values in Git)
      |
      v
ArgoCD (watches Git repo, detects the values.yaml change)
      |
      v
Kubernetes cluster (auto-syncs staging/production namespaces)
      |
      v
Prometheus + Grafana (monitors health, liveness/readiness probes auto-restart bad pods)
```

## Prerequisites (install these first)

- Docker Desktop: https://docs.docker.com/get-docker/
- kubectl: https://kubernetes.io/docs/tasks/tools/
- Minikube: https://minikube.sigs.k8s.io/docs/start/
- Helm: https://helm.sh/docs/intro/install/
- A Docker Hub account (free): https://hub.docker.com/
- A DigitalOcean account if you want the Terraform part live (has a free trial credit)

## Step 1 — Run it locally first (no Kubernetes yet)

Get the basics working before adding cluster complexity.

```bash
cd cloudpulse
docker compose up --build
```

Visit:
- http://localhost:8000/docs — FastAPI's auto-generated API docs
- http://localhost:8000/health — health check
- http://localhost:9090 — Prometheus
- http://localhost:3000 — Grafana (login: admin / admin)

Run the tests locally too, so you understand what the CI pipeline is doing:

```bash
cd app
pip install -r requirements.txt
pytest -v
```

## Step 2 — Start Minikube and deploy with Helm

```bash
minikube start
minikube addons enable ingress

# Build the image directly into Minikube's Docker so you don't need a registry yet
eval $(minikube docker-env)
docker build -t YOUR_DOCKERHUB_USERNAME/cloudpulse-api:latest ./app

# Install using Helm
helm install cloudpulse ./helm-chart/cloudpulse

# Check it's running
kubectl get pods
kubectl get svc
```

To see it self-heal: kill a pod manually and watch Kubernetes bring it back.

```bash
kubectl get pods
kubectl delete pod <pod-name>
kubectl get pods -w   # watch a new one get created automatically
```

## Step 3 — Push image to Docker Hub (needed for CI/CD to work)

```bash
docker login
docker tag YOUR_DOCKERHUB_USERNAME/cloudpulse-api:latest YOUR_DOCKERHUB_USERNAME/cloudpulse-api:latest
docker push YOUR_DOCKERHUB_USERNAME/cloudpulse-api:latest
```

## Step 4 — Set up GitHub Actions CI/CD

1. Push this whole project to a new GitHub repo.
2. In your repo settings, go to Settings -> Secrets and variables -> Actions, and add:
   - `DOCKERHUB_USERNAME`
   - `DOCKERHUB_TOKEN` (create one at hub.docker.com -> Account Settings -> Security)
3. Replace `YOUR_DOCKERHUB_USERNAME` in `.github/workflows/ci-cd.yml`, `helm-chart/cloudpulse/values.yaml`,
   and the ArgoCD manifests with your actual Docker Hub username.
4. Create a `develop` branch for staging deploys, keep `main` for production:
   ```bash
   git checkout -b develop
   git push -u origin develop
   ```
5. Push a small code change and watch the Actions tab run: test -> build -> push image -> update Helm values.

## Step 5 — Install ArgoCD and connect it to your repo

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Access the ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Get the initial admin password:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

Visit https://localhost:8080, log in with `admin` and that password.

Apply your Application manifests so ArgoCD starts watching your repo:
```bash
kubectl apply -f argocd/staging-app.yaml
kubectl apply -f argocd/production-app.yaml
```

Now, whenever GitHub Actions updates the image tag in `values-staging.yaml` or
`values-production.yaml`, ArgoCD detects the Git change and automatically
re-syncs the cluster — this is the actual "GitOps" loop.

## Step 6 — (Optional but resume-strong) Provision real infrastructure with Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with your real DigitalOcean API token
terraform init
terraform plan
terraform apply
```

This spins up a real cloud server you could install Kubernetes on (e.g. with
`k3s` for a lightweight single-node cluster) instead of using local Minikube.

## Step 7 — Monitoring dashboards

Prometheus is already scraping `/metrics` from the FastAPI app (via
`prometheus-fastapi-instrumentator`). In Grafana:
1. Add Prometheus as a data source (URL: `http://prometheus:9090` if using
   docker-compose, or the in-cluster service DNS name if on Kubernetes)
2. Import a FastAPI dashboard template or build a simple panel showing
   request count, latency, and error rate.

## What to say about this in an interview

Be ready to explain, in your own words:
- Why liveness vs. readiness probes are different (liveness = "is it stuck, restart it"; readiness = "is it ready to receive traffic")
- What GitOps means and why declarative + Git-as-source-of-truth is different from a script that runs `kubectl apply` directly
- What `selfHeal: true` in the ArgoCD Application does (reverts manual cluster changes back to match Git)
- What happens end to end when you `git push` to `main`
- Why you separated staging and production values files (safer testing before prod, different resource sizing)

## Honest scope note

This project is intentionally sized for learning and demonstrating real
concepts, not a production-grade multi-region platform. That's a fine and
expected scope for an internship-level project — the important thing is that
every piece here is real and something you can explain, not just described.

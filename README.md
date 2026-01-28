Automated CI/CD Project with GitOps

Overview

This project demonstrates a complete automated CI/CD pipeline for a backend application using modern DevOps practices.

The goal is to show how a code change can go from Git commit → validated → containerized → deployed to Kubernetes → monitored, without manual deployment steps.

The project focuses on automation, correctness, and traceability, not application complexity.

⸻

Solution Shape (T-shaped / E-shaped)

The solution is designed as a T-shaped DevOps implementation.
•	Horizontal (breadth):
The project covers the full software delivery lifecycle end-to-end — source control, CI, security scanning, image build, registry, GitOps deployment, Kubernetes runtime, and observability.
•	Vertical (depth):
A deep dive is implemented in GitOps-based deployment and immutable image versioning, including:
	•	Git as the single source of truth
	•	Automatic update of Kubernetes manifests from CI
	•	Argo CD reconciliation
	•	Immutable Docker images tagged with Git SHA

This structure demonstrates both broad understanding of the DevOps toolchain and deeper expertise in selected areas.

⸻

Application

The application is a simple FastAPI backend service.

It exposes:
	•	a basic API
	•	a /health endpoint used for Kubernetes health checks
	•   a /metrics endpoint for metrics check

The application itself is intentionally minimal so the main focus stays on the DevOps workflow.

⸻

Tools Used
	•	GitHub – source code and Git as a source of truth
	•	GitHub Actions – CI pipeline
	•	Gitleaks – secret scanning
	•	Ruff – Python linting
	•	SonarCloud – code quality and SAST
	•	Docker – container image build
	•	Trivy – container image vulnerability scanning
	•	Docker Hub – container image registry
	•	Kubernetes – application runtime
	•	Argo CD – GitOps continuous deployment
	•	Prometheus – metrics exposition format as /metrics endpoint

⸻

Continuous Integration (CI)

The CI pipeline is implemented with GitHub Actions and runs on pushes to the main branch.

Why only on main?
	•	The pipeline runs only on the main branch to ensure that only reviewed and merged code is built, scanned, and deployed, which simplifies the workflow for demo purposes.

CI responsibilities

The CI pipeline performs the following steps:
	1.	Scan the code for hardcoded secrets (Gitleaks)
	2.	Run linting checks (Ruff)
	3.	Analyze code quality and security (SonarCloud)
	4.	Build a Docker image
	5.	Scan the image for vulnerabilities (Trivy)
	6.	Push the image to Docker Hub
	7.	Update the Kubernetes deployment manifest with the new image version

Security and quality checks are executed early in the pipeline, following shift-left principles.

⸻

Image Versioning with Git SHA

Docker images are tagged using the Git commit SHA.

Each CI run builds an image with a unique tag based on the commit that triggered the pipeline.

This ensures that:
	•	every image is immutable — once it’s created it cannot be modified
	•	each deployment is traceable to a specific commit
	•	no image tag is ever overwritten
	•	the latest tag is avoided on purpose

This solves common problems where deployments run unknown or overridden image versions.

⸻

Automatic Update of deployment.yaml

As part of the CI pipeline, the Kubernetes deployment.yaml file is updated automatically with the new image tag (Git SHA).

What happens:
	•	CI replaces the image tag in deployment.yaml with the new SHA
	•	CI commits this change back to the Git repository
	•	Git now contains the updated desired state

This step is critical because it connects CI to CD in a GitOps-friendly way.

⸻

Continuous Deployment (CD) with GitOps

Deployment is handled by Argo CD using the GitOps model:
	•	Git defines the desired Kubernetes state
	•	Argo CD watches the repository for changes
	•	When deployment.yaml changes, Argo CD deploys the new version automatically

CI does not deploy directly to Kubernetes.
Argo CD is the only component that applies changes to the cluster.

⸻

Kubernetes Deployment

The application is deployed as a Kubernetes Deployment with multiple replicas:
	•	multiple replicas demonstrate availability
	•	Kubernetes Services load-balance traffic
	•	CPU and memory requests/limits are defined

This setup reflects common production Kubernetes practices.

⸻

Health Checks

The application exposes a /health endpoint:
	•	used for Kubernetes liveness and readiness checks
	•	returns a simple success response
	•	provides a binary healthy / unhealthy signal

The /health endpoint is not a monitoring solution.

⸻

Observability

Basic observability is implemented by exposing application and runtime metrics via a /metrics endpoint.

The application exposes metrics in a Prometheus-compatible format, which allows monitoring systems to scrape and collect data about the service.

The /metrics endpoint is exposed at application level using prometheus-fastapi-instrumentator, which automatically collects HTTP and process metrics and makes them available for Prometheus scraping.

The exposed metrics include:
	•	application HTTP request metrics
	•	process-level metrics (CPU, memory)
	•	runtime behavior of the service

This setup demonstrates how an application can be made observable and ready for monitoring integrations, even if a full Prometheus and Grafana stack is not fully configured in this project.

⸻

CI Execution Environment

The CI pipeline runs on ephemeral GitHub-hosted runners using ubuntu-latest:
	•	runners are temporary and destroyed after each run
	•	they are not production environments
	•	strict immutability is enforced on application images, not on CI runners

⸻

Scope and Limitations

The following items were intentionally left out to keep the project focused and understandable and are considered next logical steps:
	•	Multiple environments (dev / staging / prod) – A single environment is used to reduce configuration complexity and keep the GitOps flow easy to demonstrate.
	•	Application-level Prometheus metrics (/metrics) – Only infrastructure-level metrics are collected to demonstrate basic observability.
	•	Progressive delivery mechanisms (canary or blue-green) – A standard Kubernetes Deployment is used for simplicity.
	•	Advanced secret management solutions – The application does not consume runtime secrets; only secret scanning is demonstrated.
	•	Alerting and SLO definitions – Metrics are visualized but not coupled with alerts.

⸻

Future Improvements
	•	keep a cleaner git commit history
	•	enable CI on pull requests to validate code changes before they are merged into the main branch
	•	introduce Helm or Kustomize if the project grows to multiple environments
	•	change Docker image versioning from Git SHA to semantic versioning for better readability
	•   more "as-code" setups like dashboard-configmap.yaml for grafana dashboard

⸻

Summary

This project demonstrates:
	•	a full CI pipeline with security and quality checks
	•	immutable Docker images tagged with Git SHA
	•	automatic update of Kubernetes manifests
	•	GitOps-based deployment with Argo CD
	•	basic observability with Prometheus and Grafana

The result is a fully automated, traceable, and reproducible delivery workflow.

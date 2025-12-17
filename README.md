

# Architecting the Python Workspace: From Single Apps to Microservices
Setting up a robust development environment is the first step toward software engineering excellence. A proper setup ensures reproducibility, prevents dependency conflicts ("dependency hell"), and streamlines the coding experience.

This guide outlines the professional standard for setting up Python projects in three scenarios:

1. **The Foundation:** Essential tools for all Python developers.
2. **The Standard Project:** Best practices for a single application.
3. **Microservices (Monorepo):** Managing multiple services in one repository.
4. **Microservices (Multi-Repo):** Orchestrating distributed repositories locally.

---

## 1: The Foundation (Global Setup)
Before writing code, you must secure your toolchain. The golden rule is **never use the System Python** for development.

### 1.1 Managing Versions with `pyenv`
**Pyenv** allows you to install multiple versions of Python in user space without affecting the Operating System.

* **Install a specific version:**
```bash
pyenv install 3.11.5

```


* **Check available versions:**
```bash
pyenv versions

```



### 1.2 Isolating Dependencies with `pyenv-virtualenv`
While `pyenv` isolates Python *versions*, `pyenv-virtualenv` isolates *libraries*. This ensures Project A’s dependencies do not clash with Project B’s.

* **Create a virtual environment:**
```bash
# Syntax: pyenv virtualenv <version> <env_name>
pyenv virtualenv 3.11.5 my-project-env

```



---

## 2: The Standard Project (Single Application)
This is the default setup for monoliths, scripts, or standalone applications.

### 2.1 The "Src Layout" Structure
Modern Python standards recommend hiding source code inside a `src/` directory to prevent import errors and enforce proper packaging.

```text
my-app/
│
├── .vscode/               # Editor configuration
│   └── settings.json
├── src/                   # Source Code
│   ├── __init__.py
│   ├── main.py
│   └── modules/
├── tests/                 # Unit Tests
├── .env                   # Secrets (API Keys, DB Passwords)
├── .gitignore             # Git exclusions
├── pyproject.toml         # Tooling config (Black, Isort)
└── requirements.txt       # Dependencies

```

### 2.2 VS Code Workspace Configuration
Create a `.vscode/settings.json` file in your project root to bind the virtual environment and enforce auto-formatting.

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.analysis.extraPaths": ["${workspaceFolder}/src"],
  "editor.formatOnSave": true,
  "python.analysis.typeCheckingMode": "basic",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}

```

### 2.3 Tooling Configuration (`pyproject.toml`)
We use **Black** (formatter) and **Isort** (import sorter). Configure them to work together in `pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 88

```

---

## 3: Microservices - Monorepo Strategy
**Scenario:** You have multiple services (e.g., Auth, Order, Payment) but you want to keep them in a **Single Git Repository** for easier code sharing and refactoring.

### 3.1 Directory Structure
Each service must be treated as an isolated application with its own virtual environment.

```text
ecommerce-monorepo/
│
├── services/
│   ├── auth-service/
│   │   ├── .venv/            # Unique venv for Auth
│   │   ├── src/
│   │   ├── .env
│   │   └── requirements.txt
│   │
│   └── order-service/
│       ├── .venv/            # Unique venv for Order
│       ├── src/
│       └── requirements.txt
│
├── shared/                   # Shared Libraries
│   └── common-utils/
│
├── docker-compose.yml        # Orchestration
└── ecommerce.code-workspace  # <--- The Key File

```

### 3.2 The Multi-Root Workspace Strategy
VS Code cannot natively handle multiple virtual environments effectively if you just open the root folder. You must use a **Workspace File**.

1. Create `ecommerce.code-workspace` in the root.
2. Define each service as a distinct "folder":

```json
{
  "folders": [
    { "name": "ROOT", "path": "." },
    { "name": "Auth Service", "path": "services/auth-service" },
    { "name": "Order Service", "path": "services/order-service" }
  ],
  "settings": {
    "editor.formatOnSave": true
  }
}

```

### 3.3 Handling Shared Libraries
To use code from `shared/` without duplicating it, use **Editable Installs**:

In `services/auth-service/requirements.txt`:

```text
fastapi
-e ../../shared/common-utils

```

This creates a symbolic link, so changes in the shared folder are immediately reflected in the service.

---

## 4: Microservices - Multi-Repo Strategy (Polyrepo)
**Scenario:** Each service has its own **Separate Git Repository**. This is common in large teams where services are decoupled and deployed independently.

### 4.1 The "Meta-Folder" Structure
Since repositories are scattered, you need a local "Meta-Folder" (non-git) to house them side-by-side.

```text
MyProject-Dev/             # Local folder (Not a Git Repo)
│
├── auth-service/          # Git Clone of Repo A
│   ├── .git/
│   ├── .venv/
│   └── src/
│
├── order-service/         # Git Clone of Repo B
│   ├── .git/
│   └── src/
│
├── infrastructure/        # Git Clone of DevOps Repo
│   ├── .git/
│   └── docker-compose.yml
│
└── project.code-workspace # Local Workspace Config

```

### 4.2 Workflow Adjustments
1. **Environment Setup:** You must manually enter each folder and create a virtual environment:
```bash
cd auth-service && pyenv local 3.11.5 && pyenv virtualenv ...
cd ../order-service && pyenv local 3.10.0 && pyenv virtualenv ...

```


2. **VS Code Configuration:**
Use the **"Add Folder to Workspace"** feature in VS Code to select `auth-service`, `order-service`, and `infrastructure`. Save this as `project.code-workspace`.
3. **Orchestration (Docker):**
Since there is no root repo, create a dedicated `infrastructure` repository. The `docker-compose.yml` inside it should use relative paths to step back and access sibling directories:
```yaml
services:
  auth:
    build: ../auth-service  # Steps back to MyProject-Dev, then into auth
    volumes:
      - ../auth-service:/app

```


4. **Shared Libraries in Multi-Repo:**
* **Local Dev:** Use `pip install -e ../shared-repo`.
* **Production:** In `requirements.txt`, point to the git URL:
```text
git+ssh://git@github.com/company/shared-lib.git@v1.0.0

```





---

## Summary: Which Structure to Choose?
| Feature | Standard Project | Monorepo Microservices | Multi-Repo Microservices |
| --- | --- | --- | --- |
| **Complexity** | Low | Medium | High |
| **Git Repos** | 1 | 1 | Many |
| **VS Code Mode** | Open Folder | **Multi-Root Workspace** | **Multi-Root Workspace** |
| **Dependency Mgmt** | Single `requirements.txt` | Multiple `.venv` inside subfolders | Multiple `.venv` in separate folders |
| **Best For** | Monoliths, Scripts | Startups, Small-Medium Teams | Enterprises, Independent Teams |

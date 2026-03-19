import json
import re
import requests
from requests.auth import HTTPBasicAuth

# Odoo connection settings
ODOO_URL = "http://34.230.6.219:8069/jsonrpc"
ODOO_DB = "odoo_lab"
ODOO_LOGIN = "bby.dmo.01@outlook.com"
ODOO_PASSWORD = "admin"

# OpenProject connection settings
OPENPROJECT_BASE = "http://34.230.6.219:8080"
OPENPROJECT_API_TOKEN = "44d6e196b1fb337cf88a2eca2d09d2a8c891eb8b279d2edae3cf218b7661025d"


# Convert project name into OpenProject-friendly identifier
def slugify(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


# Generic Odoo JSON-RPC call
def odoo_call(service, method, *args):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": service,
            "method": method,
            "args": list(args)
        },
        "id": 1
    }

    response = requests.post(ODOO_URL, json=payload)
    print(f"Odoo status: {response.status_code}")

    data = response.json()
    if "error" in data:
        raise Exception(json.dumps(data["error"], indent=2))

    return data["result"]


# Authenticate to Odoo and get user ID
def get_odoo_uid():
    return odoo_call("common", "login", ODOO_DB, ODOO_LOGIN, ODOO_PASSWORD)


# Read all Odoo projects
def get_odoo_projects(uid):
    return odoo_call(
        "object",
        "execute_kw",
        ODOO_DB,
        uid,
        ODOO_PASSWORD,
        "project.project",
        "search_read",
        [[]],
        {"fields": ["id", "name"]}
    )


# OpenProject uses Basic auth with username "apikey" and password = token
def openproject_auth():
    return HTTPBasicAuth("apikey", OPENPROJECT_API_TOKEN)


def openproject_headers():
    return {
        "Content-Type": "application/json"
    }


# Check whether a project already exists in OpenProject
def openproject_project_exists(identifier):
    url = f"{OPENPROJECT_BASE}/api/v3/projects/{identifier}"
    response = requests.get(
        url,
        headers=openproject_headers(),
        auth=openproject_auth()
    )
    print(f"OpenProject check [{identifier}] status: {response.status_code}")
    return response.status_code == 200


# Create project in OpenProject
def create_openproject_project(name, identifier):
    url = f"{OPENPROJECT_BASE}/api/v3/projects"
    payload = {
        "name": name,
        "identifier": identifier
    }

    response = requests.post(
        url,
        headers=openproject_headers(),
        auth=openproject_auth(),
        json=payload
    )
    print(f"OpenProject create [{identifier}] status: {response.status_code}")

    if response.status_code not in (200, 201):
        print("Create failed:")
        print(response.text)
        return False

    print("Created successfully.")
    return True


def main():
    # Step 1: login to Odoo
    uid = get_odoo_uid()
    print(f"Odoo UID: {uid}")

    # Step 2: get all Odoo projects
    projects = get_odoo_projects(uid)
    print(f"Found {len(projects)} Odoo projects")

    # Step 3: sync each project safely
    for project in projects:
        project_id = project["id"]
        project_name = project["name"]
        identifier = slugify(project_name)

        print("\n---")
        print(f"Odoo project: {project_name} (id={project_id})")
        print(f"OpenProject identifier: {identifier}")

        if openproject_project_exists(identifier):
            print("Already exists in OpenProject. Skipping.")
            continue

        create_openproject_project(project_name, identifier)


if __name__ == "__main__":
    main()

from flask import Blueprint, jsonify, Response
import json

bp = Blueprint("docs", __name__)


def _openapi_spec() -> dict:
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "SSH Log Tools API",
            "version": "1.0.0",
            "description": "Local API for logs, profiles, records, and images.",
        },
        "tags": [
            {"name": "Logs", "description": "Inspect and search local log files."},
            {"name": "Profiles", "description": "Manage remote connection profiles and their paths."},
            {"name": "Records", "description": "Create records and attach images and tags."},
        ],
        "paths": {
            "/api/logs": {
                "get": {
                    "tags": ["Logs"],
                    "summary": "List local logs",
                    "description": "Return configured log files with size and modification time.",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/logs/{name}/tail": {
                "get": {
                    "tags": ["Logs"],
                    "summary": "Tail local log",
                    "description": "Fetch the last N lines from the log file. Use the 'lines' query parameter to control how many lines are returned.",
                    "parameters": [
                        {"name": "name", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "lines", "in": "query", "schema": {"type": "integer", "description": "Number of lines from end of file"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/logs/{name}/search": {
                "get": {
                    "tags": ["Logs"],
                    "summary": "Search local log",
                    "description": "Search a log file for text or regular expressions. Supports context lines, regex mode, and case sensitivity.",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/profiles": {
                "get": {
                    "tags": ["Profiles"],
                    "summary": "List profiles",
                    "description": "Return configured remote connection profiles with any registered paths.",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "tags": ["Profiles"],
                    "summary": "Create profile",
                    "description": "Create a new remote connection profile. At minimum a name and host must be provided.",
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/api/profiles/{id}": {
                "put": {
                    "tags": ["Profiles"],
                    "summary": "Update profile",
                    "description": "Modify fields on an existing profile identified by its ID.",
                    "responses": {"200": {"description": "OK"}},
                },
                "delete": {
                    "tags": ["Profiles"],
                    "summary": "Delete profile",
                    "description": "Remove a profile by ID along with its registered paths.",
                    "responses": {"200": {"description": "OK"}},
                },
            },
            "/api/profiles/{id}/paths": {
                "get": {
                    "tags": ["Profiles"],
                    "summary": "List registered paths",
                    "description": "Return paths monitored for a profile.",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "tags": ["Profiles"],
                    "summary": "Add registered path",
                    "description": "Register a new path or glob pattern for the profile.",
                    "responses": {"200": {"description": "OK"}},
                },
            },
            "/api/profile_paths/{ppid}": {
                "put": {
                    "tags": ["Profiles"],
                    "summary": "Update registered path",
                    "description": "Modify an existing registered path entry by its ID.",
                    "responses": {"200": {"description": "OK"}},
                },
                "delete": {
                    "tags": ["Profiles"],
                    "summary": "Delete registered path",
                    "description": "Remove a registered path entry by its ID.",
                    "responses": {"200": {"description": "OK"}},
                },
            },
            "/api/profiles/{id}/ping": {
                "get": {
                    "tags": ["Profiles"],
                    "summary": "Ping SSH connectivity",
                    "description": "Attempt a lightweight SSH connection to verify credentials.",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/profiles/{id}/list": {
                "get": {
                    "tags": ["Profiles"],
                    "summary": "Expand remote glob to files",
                    "description": "List files matching a remote glob expression via the profile.",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/profiles/{id}/cat": {
                "get": {
                    "tags": ["Profiles"],
                    "summary": "Tail remote file",
                    "description": "Fetch the last N lines from a remote file using the profile's connection settings.",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/records": {
                "get": {
                    "tags": ["Records"],
                    "summary": "List records",
                    "description": "Retrieve recorded events optionally filtered by tag or date range.",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "tags": ["Records"],
                    "summary": "Create record",
                    "description": "Create a new record entry with optional tags and images.",
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/api/records/{id}": {
                "put": {
                    "tags": ["Records"],
                    "summary": "Update record",
                    "description": "Modify fields on an existing record.",
                    "responses": {"200": {"description": "OK"}},
                },
                "delete": {
                    "tags": ["Records"],
                    "summary": "Delete record",
                    "description": "Remove a record and its images.",
                    "responses": {"200": {"description": "OK"}},
                },
            },
            "/api/records/{id}/image": {
                "post": {
                    "tags": ["Records"],
                    "summary": "Upload image for record",
                    "description": "Upload an image file and associate it with a record.",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/records/{id}/image_remote": {
                "post": {
                    "tags": ["Records"],
                    "summary": "Fetch and attach remote image",
                    "description": "Download an image from a remote URL and attach it to the record.",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/record_images/{iid}": {
                "delete": {
                    "tags": ["Records"],
                    "summary": "Delete record image",
                    "description": "Remove an image associated with a record by its ID.",
                    "responses": {"200": {"description": "OK"}},
                }
            },
        },
    }


@bp.get("/openapi.json")
def openapi_json():
    return jsonify(_openapi_spec())


@bp.get("/docs")
def swagger_ui():
    # Simple Swagger UI via CDN
    html = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset='utf-8'>
        <title>API Docs - SSH Log Tools</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
        <style> body {{ margin:0; background:#E9FEE1; }} #swagger-ui {{ max-width: 100%; }}</style>
      </head>
      <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script>
          window.ui = SwaggerUIBundle({{ url: '/openapi.json', dom_id: '#swagger-ui' }});
        </script>
      </body>
    </html>
    """
    return Response(html, mimetype="text/html")


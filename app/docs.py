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
        "paths": {
            "/api/logs": {"get": {"summary": "List local logs", "responses": {"200": {"description": "OK"}}}},
            "/api/logs/{name}/tail": {"get": {"summary": "Tail local log", "parameters": [{"name": "name", "in": "path", "required": True, "schema": {"type": "string"}}, {"name": "lines", "in": "query", "schema": {"type": "integer"}}], "responses": {"200": {"description": "OK"}}}},
            "/api/logs/{name}/search": {"get": {"summary": "Search local log", "responses": {"200": {"description": "OK"}}}},
            "/api/profiles": {"get": {"summary": "List profiles", "responses": {"200": {"description": "OK"}}}, "post": {"summary": "Create profile", "responses": {"201": {"description": "Created"}}}},
            "/api/profiles/{id}": {"put": {"summary": "Update profile", "responses": {"200": {"description": "OK"}}}, "delete": {"summary": "Delete profile", "responses": {"200": {"description": "OK"}}}},
            "/api/profiles/{id}/paths": {"get": {"summary": "List registered paths", "responses": {"200": {"description": "OK"}}}, "post": {"summary": "Add registered path", "responses": {"200": {"description": "OK"}}}},
            "/api/profile_paths/{ppid}": {"put": {"summary": "Update registered path", "responses": {"200": {"description": "OK"}}}, "delete": {"summary": "Delete registered path", "responses": {"200": {"description": "OK"}}}},
            "/api/profiles/{id}/ping": {"get": {"summary": "Ping SSH connectivity", "responses": {"200": {"description": "OK"}}}},
            "/api/profiles/{id}/list": {"get": {"summary": "Expand remote glob to files", "responses": {"200": {"description": "OK"}}}},
            "/api/profiles/{id}/cat": {"get": {"summary": "Tail remote file (last N lines)", "responses": {"200": {"description": "OK"}}}},
            "/api/records": {"get": {"summary": "List records", "responses": {"200": {"description": "OK"}}}, "post": {"summary": "Create record", "responses": {"201": {"description": "Created"}}}},
            "/api/records/{id}": {"put": {"summary": "Update record", "responses": {"200": {"description": "OK"}}}, "delete": {"summary": "Delete record", "responses": {"200": {"description": "OK"}}}},
            "/api/records/{id}/image": {"post": {"summary": "Upload image for record", "responses": {"200": {"description": "OK"}}}},
            "/api/records/{id}/image_remote": {"post": {"summary": "Fetch and attach remote image", "responses": {"200": {"description": "OK"}}}},
            "/record_images/{iid}": {"delete": {"summary": "Delete record image", "responses": {"200": {"description": "OK"}}}},
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
        <style> body {{ margin:0; background:#0f172a; }} #swagger-ui {{ max-width: 100%; }}</style>
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


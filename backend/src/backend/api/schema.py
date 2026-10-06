from fastapi.openapi.utils import get_openapi

from backend.api.session import SESSION_COOKIE


def api_schema(app):
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    schema["components"]["securitySchemes"] = {
        "LocalSession": {"type": "apiKey", "in": "cookie", "name": SESSION_COOKIE},
    }
    schema["security"] = [{"LocalSession": []}]
    models = schema["components"]["schemas"]
    models["ErrorEnvelope"] = {
        "type": "object", "required": ["error"], "properties": {
            "error": {"type": "object", "required": ["code", "message"], "properties": {
                "code": {"type": "string"}, "message": {"type": "string"},
            }},
        },
    }
    models.pop("HTTPValidationError", None)
    models.pop("ValidationError", None)
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            public = (method, path) in {("get", "/health"), ("post", "/session")}
            if public:
                operation["security"] = []
            for status in (400, 401, 403, 404, 409, 422, 500, 502, 503):
                if status == 401 and public:
                    continue
                operation["responses"][str(status)] = {
                    "description": "统一错误；具体触发条件见接口基线",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorEnvelope"}}},
                }
            if method == "get" and path.endswith("/events"):
                operation["responses"]["200"]["content"] = {"text/event-stream": {"schema": {"type": "string"}}}
            if (method, path) in {("post", "/data/export"), ("get", "/data/backups/{backup_id}")}:
                operation["responses"]["200"]["content"] = {"application/zip": {"schema": {"type": "string", "format": "binary"}}}
    app.openapi_schema = schema
    return schema

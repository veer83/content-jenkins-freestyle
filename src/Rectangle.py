def filter_swagger_content(raw_content):
    swagger_lines = []
    capture = False
    paths_data = []

    # Capture only valid Swagger lines
    for line in raw_content.splitlines():
        if "openapi" in line or "swagger" in line:
            capture = True
        if capture:
            swagger_lines.append(line)

    if not swagger_lines:
        return None, "", {}, []

    try:
        fixed_content = "\n".join(swagger_lines)
        swagger_json = json.loads(fixed_content)

        # Extract basepath
        basepath = ""
        if "basePath" in swagger_json:
            basepath = swagger_json["basePath"]
        elif "servers" in swagger_json:
            basepath = swagger_json["servers"][0].get("url", "")

        # Extract info data
        info_data = swagger_json.get("info", {})
        x_dataclassification_code = swagger_json.get("x-dataclassification-code", "N/A")

        # Extract paths
        for path, methods in swagger_json.get("paths", {}).items():
            for method, details in methods.items():
                paths_data.append({
                    "path": path,
                    "verb": method.upper(),
                    "dataclassification_code": details.get("x-dataclassification-code", "N/A")
                })

        return swagger_json, basepath, info_data, paths_data

    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}. Content skipped.")
        return None, "", {}, []



if swagger_content:
    swagger_file_path = save_swagger_file(name, version, swagger_content)
    if swagger_file_path:
        push_to_database(
            product, plan.get("name"), name, version, swagger_content,
            basepath, env, space, org, created_date, updated_date, info_data, paths_data
        )

def filter_swagger_content(raw_content):
    swagger_lines = []
    capture = False
    basepath = ""
    info_data = {}
    dataclassification_code = ""
    paths_data = []

    for line in raw_content.splitlines():
        if "openapi" in line or "swagger" in line:
            capture = True
        if capture:
            swagger_lines.append(line)

    if not swagger_lines:
        return None, "", {}, []

    try:
        filtered_content = "\n".join(swagger_lines)
        swagger_json = json.loads(filtered_content)

        # Extract basepath
        if "basePath" in swagger_json:
            basepath = swagger_json["basePath"]
        elif "servers" in swagger_json:
            basepath = swagger_json["servers"][0].get("url", "")

        # Extract API info
        info = swagger_json.get("info", {})
        info_data = {
            "api_name": info.get("title", ""),
            "api_version": info.get("version", ""),
            "description": info.get("description", ""),
            "x_ibm_name": info.get("x-ibm-name", ""),
            "x_template_version": info.get("x-template-version", "")
        }

        # Extract paths and classification code
        if "paths" in swagger_json:
            for path, methods in swagger_json["paths"].items():
                for method, details in methods.items():
                    dataclassification_code = details.get("x-dataclassification-code", "N/A")
                    paths_data.append({
                        "path": path,
                        "verb": method.upper(),
                        "dataclassification_code": dataclassification_code
                    })

        return swagger_json, basepath, info_data, paths_data

    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}")
        return None, "", {}, []

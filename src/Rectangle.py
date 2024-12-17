


def download_swagger(env, catalog, product_list, space, org):
    for product in product_list.get("results", []):
        created_date = product.get("created_at", "N/A")
        updated_date = product.get("updated_at", "N/A")
        for plan in product.get("plans", []):
            for api in plan.get("apis", []):
                name, version = api.get("name"), api.get("version")
                if name and version:
                    logging.info(f"Processing API: {name} with version: {version} under product: {product.get('name')} and plan: {plan.get('name')}")
                    
                    get_swagger_command = [
                        GET_SWAGGER_SCRIPT, env, f"{name}:{version}", catalog, OUTPUT_DIR
                    ]
                    result = run_command(
                        get_swagger_command,
                        None,
                        f"Error downloading Swagger for {name}:{version}",
                        capture_output=True
                    )

                    swagger_content, basepath, info_data = filter_swagger_content(result.stdout)
                    
                    if swagger_content:
                        swagger_file_path = save_swagger_file(name, version, swagger_content)
                        if swagger_file_path:
                            push_to_database(
                                product, plan, name, version, swagger_content,
                                basepath, env, space, org, created_date, updated_date, info_data
                            )
                    else:
                        logging.warning(f"No relevant Swagger content found for {name}:{version}")
                else:
                    logging.warning(f"Skipping API with missing name or version: {api}")


def save_swagger_file(name, version, content):
    swagger_output_file = os.path.join(OUTPUT_DIR, f"{name}_{version}.json")
    try:
        with open(swagger_output_file, 'w') as output_file:
            output_file.write(json.dumps(content, indent=4))  # Serialize content to JSON
        logging.info(f"Swagger successfully saved to {swagger_output_file}")
        return swagger_output_file
    except Exception as e:
        logging.error(f"Failed to save Swagger for {name}:{version}: {e}")
        return None



def process_product_list(env, catalog, space, org, product_list):
    download_swagger(env, catalog, product_list, space, org)

def main():
    setup_output_directory()
    env = input("Enter environment: ")
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    catalog = input("Enter catalog name: ")
    space = input("Enter space name: ")
    org = input("Enter org name: ")

    list_products(env, catalog, space)
    product_list = load_product_list()

    if not product_list:
        logging.error("Exiting due to empty or invalid product list.")
        exit(1)

    process_product_list(env, catalog, space, org, product_list)
    logging.info("Completed all operations successfully.")

if __name__ == "__main__":
    main()

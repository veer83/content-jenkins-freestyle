def list_products(env, catalog, space):
    command = [
        "sudo",
        LIST_PRODUCTS_SCRIPT,
        "--server", env,
        "--catalog", catalog,
        "--space", space,
        "--output", OUTPUT_DIR
    ]
    
    run_command(
        command,
        "Product list downloaded successfully.",
        "Error downloading product list"
    )


def process_product(product, env, space, org, catalog):

    product_name = product.get('name')
    product_version = product.get('version')
    logger.info(f"Processing product: {product_name}")

    swagger_command = ["sudo", GET_SWAGGER_SCRIPT, env, f"{product_name}:{product_version}", catalog, OUTPUT_DIR]
    try:
        result = run_command(swagger_command, "Swagger downloaded successfully", "Error downloading Swagger", capture_output=True)
    except CommandError:
        logger.error(f"Skipping product {product_name} due to fetch error.")
        return

    swagger_json, basepath, info_data, paths_data = filter_swagger_content(result.stdout)
    if swagger_json:
        created_date = product.get("created_date", "")
        updated_date = product.get("updated_date", "")
        push_to_database(
            product,
            swagger_json,
            basepath,
            env,
            space,
            org,
            created_date,
            updated_date,
            info_data,
            paths_data
        )
    else:
        logger.warning(f"No valid swagger extracted for product {product_name}, skipping.")

def process_products(product_list, env, space, org, catalog):
    for product in product_list.get("results", []):
        process_product(product, env, space, org, catalog)

def main():
    try:
        config = load_config()
        setup_output_directory()

        env = config.get("environment")
        username = config.get("username")
        password = config.get("password")
        catalog = config.get("catalog")
        # We'll assume space is known from config since login does not provide it.
        space = config.get("space")

        # Login and get environment info from the text output
        env_found, space_found, org_found = login(env, username, password)
        
        # If login extracted env, org but not space, use config space as fallback:
        if space_found is None:
            space_found = space

        # Download product list with correct arguments
        list_products(env_found, catalog, space_found)

        # Load product list from downloaded YAML
        product_list = load_product_list()
        if not product_list:
            logger.error("Exiting due to empty or invalid product list.")
            sys.exit(1)

        # Process each product
        process_products(product_list, env_found, space_found, org_found, catalog)
        logger.info("Completed all operations successfully.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

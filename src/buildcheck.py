from openshift.dynamic import DynamicClient
from kubernetes import client, config

def find_buildconfigs_in_project(namespace, uri, ref, context_dir):
    """
    Search for all BuildConfigs in a specific OpenShift project (namespace)
    that match the given repository URI, reference (branch), and context directory.
    """
    # Load Kubernetes/OpenShift configuration
    config.load_kube_config()
    k8s_client = client.ApiClient()
    dyn_client = DynamicClient(k8s_client)

    # Access BuildConfig resources
    v1_bc = dyn_client.resources.get(api_version="build.openshift.io/v1", kind="BuildConfig")

    # Fetch all BuildConfigs in the namespace
    buildconfigs = v1_bc.get(namespace=namespace).items

    # Iterate through the BuildConfigs and look for matches
    matching_buildconfigs = []
    for bc in buildconfigs:
        try:
            source = bc.spec.source
            if (
                source.git.uri == uri and
                source.git.ref == ref and
                source.contextDir == context_dir
            ):
                matching_buildconfigs.append({
                    "name": bc.metadata.name,
                    "namespace": bc.metadata.namespace
                })
        except AttributeError:
            # Skip BuildConfigs that don't have required fields
            continue

    # Output the results
    if matching_buildconfigs:
        print(f"Matching BuildConfigs found in namespace '{namespace}':")
        for match in matching_buildconfigs:
            print(f"  - Name: {match['name']}")
    else:
        print(f"No matching BuildConfigs found in namespace '{namespace}'.")
    return matching_buildconfigs


# Get user input for the namespace
project_namespace = input("Enter the OpenShift project/namespace to search: ").strip()

# Replace these values with your specific criteria
repository_uri = 't'
branch_ref = 's'
context_directory = 'boot'

# Run the function
find_buildconfigs_in_project(project_namespace, repository_uri, branch_ref, context_directory)

import boto3
from botocore.exceptions import ClientError
import datetime
import json
import subprocess
import os
import sys


TERRAFORM_DIR = os.path.join(
    os.path.dirname(__file__), "../terraform"
)  # Folder containing the Terraform files


def get_terraform_outputs():
    """Get the outputs of Terraform in JSON format."""
    print(f"🔍 Reading Terraform configuration from {TERRAFORM_DIR}...")
    try:
        # Run 'terraform output -json' to get the real values
        cmd = ["terraform", "output", "-json"]
        result = subprocess.run(
            cmd, cwd=TERRAFORM_DIR, capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError:
        print("❌ Error: Unable to read Terraform outputs.")
        print("Make sure you ran 'terraform apply' first.")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Error: 'terraform' command not found.")
        sys.exit(1)


def find_db_instance_by_endpoint(rds, endpoint):
    """
    Find RDS instance by matching endpoint.
    Extracts the instance identifier from the endpoint and tries to find it.
    """
    try:
        # Extract instance identifier from endpoint
        # Format: instance-id.random.region.rds.amazonaws.com:port
        endpoint_host = endpoint.split(":")[0]  # Remove port
        instance_id_from_endpoint = endpoint_host.split(".")[0]

        # Try to find by the extracted identifier
        try:
            response = rds.describe_db_instances(
                DBInstanceIdentifier=instance_id_from_endpoint
            )
            return response["DBInstances"][0]
        except ClientError:
            pass

        # If that fails, list all instances and match by endpoint
        response = rds.describe_db_instances()
        for instance in response["DBInstances"]:
            if instance.get("Endpoint", {}).get("Address") == endpoint_host:
                return instance
            # Also check if endpoint matches without port
            instance_endpoint = instance.get("Endpoint", {}).get("Address", "")
            if instance_endpoint and endpoint_host.startswith(instance_endpoint):
                return instance

        return None
    except Exception as e:
        print(f"⚠️  Warning: Error while searching by endpoint: {e}")
        return None


def create_rds_snapshot():
    """
    Create a snapshot of the RDS database instance.
    The snapshot ID includes a timestamp for uniqueness.
    """
    rds = boto3.client("rds", region_name="eu-west-3")

    # Get the database instance identifier from Terraform outputs
    outputs = get_terraform_outputs()
    db_instance_id = outputs.get("rds_instance_id", {}).get("value")
    rds_endpoint = outputs.get("rds_endpoint", {}).get("value")

    if not db_instance_id:
        print("❌ Error: 'rds_instance_id' output not found in Terraform.")
        sys.exit(1)

    db_instance = None
    actual_instance_id = None

    # First, try to find the instance using the identifier from Terraform
    try:
        print(f"🔍 Verifying database instance {db_instance_id} exists...")
        response = rds.describe_db_instances(DBInstanceIdentifier=db_instance_id)
        db_instance = response["DBInstances"][0]
        actual_instance_id = db_instance["DBInstanceIdentifier"]
        db_status = db_instance["DBInstanceStatus"]
        print(f"✅ Database instance found. Status: {db_status}")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "DBInstanceNotFound":
            print(
                f"⚠️  Instance '{db_instance_id}' not found, trying to find by endpoint..."
            )
            # Try to find by endpoint as fallback
            if rds_endpoint:
                db_instance = find_db_instance_by_endpoint(rds, rds_endpoint)
                if db_instance:
                    actual_instance_id = db_instance["DBInstanceIdentifier"]
                    db_status = db_instance["DBInstanceStatus"]
                    print(
                        f"✅ Database instance found by endpoint: {actual_instance_id}"
                    )
                    print(f"   Status: {db_status}")
                else:
                    print("❌ Error: Could not find database instance.")
                    print(f"   Tried identifier: {db_instance_id}")
                    if rds_endpoint:
                        print(f"   Tried endpoint: {rds_endpoint}")
                    print(
                        "   Please verify the instance exists or run 'terraform apply' to create it."
                    )
                    sys.exit(1)
            else:
                print(
                    f"❌ Error: Database instance '{db_instance_id}' not found in AWS."
                )
                print(
                    "   The instance may have been deleted or the identifier is incorrect."
                )
                print(
                    "   Please verify the instance exists or run 'terraform apply' to create it."
                )
                sys.exit(1)
        else:
            print(f"❌ Error verifying database instance: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error verifying database instance: {e}")
        sys.exit(1)

    if not actual_instance_id:
        actual_instance_id = db_instance_id

    if db_instance and db_instance.get("DBInstanceStatus") not in [
        "available",
        "backing-up",
    ]:
        db_status = db_instance["DBInstanceStatus"]
        print(
            f"⚠️  Warning: Database instance is in '{db_status}' state. Snapshot may fail."
        )

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")
    snapshot_id = f"snap-{actual_instance_id}-{timestamp}"

    try:
        print(f"💾 Creating snapshot {snapshot_id} for {actual_instance_id}...")
        response = rds.create_db_snapshot(
            DBSnapshotIdentifier=snapshot_id, DBInstanceIdentifier=actual_instance_id
        )
        print("✅ Snapshot triggered successfully.")
        print(f"   Status: {response['DBSnapshot']['Status']}")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "DBInstanceNotFound":
            print(f"❌ Error: Database instance '{actual_instance_id}' not found.")
            print(
                "   The instance may have been deleted or the identifier is incorrect."
            )
            sys.exit(1)
        else:
            print(f"❌ Error during backup: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error during backup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_rds_snapshot()

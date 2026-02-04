import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone, timedelta
import json
import subprocess
import os
import sys


TERRAFORM_DIR = os.path.join(
    os.path.dirname(__file__), "../terraform"
)  # Folder containing the Terraform files


def get_terraform_outputs():
    """Get the outputs of Terraform in JSON format."""
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


def get_db_instance_id(rds):
    """Get the actual database instance ID from Terraform outputs."""
    outputs = get_terraform_outputs()
    db_instance_id = outputs.get("rds_instance_id", {}).get("value")
    rds_endpoint = outputs.get("rds_endpoint", {}).get("value")

    if not db_instance_id:
        print("❌ Error: 'rds_instance_id' output not found in Terraform.")
        sys.exit(1)

    # Try to verify the instance exists
    try:
        rds.describe_db_instances(DBInstanceIdentifier=db_instance_id)
        return db_instance_id
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "DBInstanceNotFound":
            print(
                f"⚠️  Instance '{db_instance_id}' not found, trying to find by endpoint..."
            )
            if rds_endpoint:
                db_instance = find_db_instance_by_endpoint(rds, rds_endpoint)
                if db_instance:
                    return db_instance["DBInstanceIdentifier"]
            print("❌ Error: Could not find database instance.")
            sys.exit(1)
        else:
            print(f"❌ Error verifying database instance: {e}")
            sys.exit(1)


def cleanup_old_snapshots(days_retention=7):
    """
    Delete old RDS manual snapshots older than the specified retention period.

    Args:
        days_retention: Number of days to retain snapshots (default: 7)
    """
    rds = boto3.client("rds", region_name="eu-west-3")

    # Get the database instance identifier
    db_instance_id = get_db_instance_id(rds)
    print(f"📋 Target database instance: {db_instance_id}")

    # Calculate the cutoff date: today minus retention days
    limit_date = datetime.now(timezone.utc) - timedelta(days=days_retention)

    print(f"🔍 Searching for manual snapshots older than {limit_date}...")
    print(f"   Retention period: {days_retention} days")

    # Retrieve all manual snapshots for this specific instance
    try:
        snapshots = rds.describe_db_snapshots(
            DBInstanceIdentifier=db_instance_id, SnapshotType="manual"
        )["DBSnapshots"]
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "DBInstanceNotFound":
            print(f"❌ Error: Database instance '{db_instance_id}' not found.")
            sys.exit(1)
        else:
            print(f"❌ Error retrieving snapshots: {e}")
            sys.exit(1)

    print(f"📊 Found {len(snapshots)} manual snapshot(s) for this instance")

    if len(snapshots) == 0:
        print("ℹ️  No snapshots found for this database instance.")
        return

    # Display all snapshots with their dates
    print("\n📸 Current snapshots:")
    for snap in snapshots:
        snap_date = snap["SnapshotCreateTime"]
        snap_id = snap["DBSnapshotIdentifier"]
        age_days = (datetime.now(timezone.utc) - snap_date).days
        status = snap.get("Status", "unknown")
        is_old = snap_date < limit_date
        marker = "🗑️  [OLD]" if is_old else "✅ [KEEP]"
        print(
            f"   {marker} {snap_id} | Created: {snap_date} | Age: {age_days} days | Status: {status}"
        )

    deleted_count = 0
    print("\n🗑️  Starting cleanup...")
    for snap in snapshots:
        snap_date = snap["SnapshotCreateTime"]
        snap_id = snap["DBSnapshotIdentifier"]
        age_days = (datetime.now(timezone.utc) - snap_date).days

        # Delete snapshots older than the retention period
        if snap_date < limit_date:
            print(
                f"   Deleting snapshot: {snap_id} (Age: {age_days} days, Created: {snap_date})"
            )
            try:
                rds.delete_db_snapshot(DBSnapshotIdentifier=snap_id)
                deleted_count += 1
                print(f"   ✅ Successfully deleted: {snap_id}")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "InvalidDBSnapshotState":
                    print(
                        f"   ⚠️  Cannot delete {snap_id}: Snapshot is in '{snap.get('Status')}' state"
                    )
                else:
                    print(f"   ⚠️  Error deleting snapshot {snap_id}: {e}")
            except Exception as e:
                print(f"   ⚠️  Error deleting snapshot {snap_id}: {e}")

    if deleted_count > 0:
        print(f"\n✅ Cleanup completed. {deleted_count} snapshot(s) deleted.")
    else:
        print(
            "\nℹ️  No old snapshots found to delete (all snapshots are within retention period)."
        )


if __name__ == "__main__":
    cleanup_old_snapshots(7)

import boto3
import sys


def manage_instances(action):
    """
    Start or stop EC2 instances based on the specified action.
    Only targets instances tagged with Environment='dev'.
    """
    ec2 = boto3.resource("ec2", region_name="eu-west-3")

    filters = [
        {"Name": "tag:Environment", "Values": ["dev"]},
        {
            "Name": "instance-state-name",
            # Filter by current state: running if we want to stop, stopped if we want to start
            "Values": ["running" if action == "stop" else "stopped"],
        },
    ]

    # Retrieve instances matching the filters
    instances = ec2.instances.filter(Filters=filters)
    instance_ids = [i.id for i in instances]

    if not instance_ids:
        print(f"ℹ️  No instances to {action}.")
        return

    # Execute the requested action (start or stop)
    if action == "stop":
        print(f"🛑 Stopping instances: {instance_ids}")
        ec2.instances.filter(InstanceIds=instance_ids).stop()
    elif action == "start":
        print(f"🚀 Starting instances: {instance_ids}")
        ec2.instances.filter(InstanceIds=instance_ids).start()


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) != 2 or sys.argv[1] not in ["start", "stop"]:
        print("❌ Usage: python daily_scheduler.py [start|stop]")
        sys.exit(1)
    else:
        manage_instances(sys.argv[1])

import boto3
from botocore.exceptions import ClientError
import json

# Cost configuration (Approximate prices for eu-west-3 if pricing API is not available)
PRICING = {
    "t3.micro": 0.0118,
    "alb": 0.0243,
    "nat_gateway": 0.048,
}


def get_real_price(instance_type, region_code="eu-west-3"):
    """
    Retrieve the On-Demand Linux price for a given instance in Paris.
    Requires a boto3 client on us-east-1.
    """
    # Mapping of region names for the Pricing API
    region_map = {
        "eu-west-3": "EU (Paris)",
    }

    location = region_map.get(region_code)
    if not location:
        return 0.0

    pricing_client = boto3.client("pricing", region_name="us-east-1")

    try:
        response = pricing_client.get_products(
            ServiceCode="AmazonEC2",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
                {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
                {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
                {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
            ],
            MaxResults=1,
        )

        # Parsing JSON response
        price_list = response["PriceList"]
        if not price_list:
            return 0.0

        item = json.loads(price_list[0])
        terms = item["terms"]["OnDemand"]
        term_key = list(terms.keys())[0]
        price_dimensions = terms[term_key]["priceDimensions"]
        price_dim_key = list(price_dimensions.keys())[0]

        price_per_unit = price_dimensions[price_dim_key]["pricePerUnit"]["USD"]
        return float(price_per_unit)

    except Exception as e:
        print(f"⚠️ Error retrieving price for {instance_type}: {e}")
        return 0.0


def audit_compute():
    """List the EC2 instances and check compliance."""
    ec2 = boto3.resource("ec2")

    print("\n🖥️  AUDIT COMPUTE (EC2)")
    print("-" * 60)

    # Only look at the instances that are running
    instances = list(
        ec2.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )
    )

    if not instances:
        print("   No running instances.")
        return 0

    hourly_cost = 0
    for i in instances:
        # Get the Name (Tag)
        name = "Inconnu"
        if i.tags:
            for tag in i.tags:
                if tag["Key"] == "Name":
                    name = tag["Value"]

        # Try to get the real price, otherwise use the approximate price
        real_price = get_real_price(i.instance_type)

        if real_price > 0:
            hourly_cost = real_price
        else:
            hourly_cost = PRICING.get(i.instance_type, 0.0)

        print(
            f"   ✅ {name:<30} | {i.instance_type:<10} | {i.placement['AvailabilityZone']:<10} | {hourly_cost}$/h"
        )

    print(f"   👉 Total Compute : {len(instances)} instances")
    return hourly_cost


def audit_network_cost():
    """Check the ALBs and NAT Gateways (which are expensive)."""
    client = boto3.client("elbv2")
    ec2_client = boto3.client("ec2")

    print("\n🌐 AUDIT NETWORK & FLOW")
    print("-" * 60)

    cost = 0

    # Load Balancers
    albs = client.describe_load_balancers()["LoadBalancers"]
    for alb in albs:
        print(f"   ⚖️  Active ALB : {alb['LoadBalancerName']} ({alb['DNSName']})")
        cost += PRICING["alb"]

    # NAT Gateways
    nats = ec2_client.describe_nat_gateways(
        Filter=[{"Name": "state", "Values": ["available"]}]
    )["NatGateways"]
    for nat in nats:
        print(f"   🌉 Active NAT Gateway : {nat['NatGatewayId']}")
        cost += PRICING["nat_gateway"]

    if not albs and not nats:
        print("   No expensive network equipment detected.")

    return cost


def audit_security_groups():
    """Check if the port 22 (SSH) is open to everyone (Security vulnerability)."""
    ec2 = boto3.resource("ec2")

    print("\n🔒 AUDIT SECURITY (Security Groups)")
    print("-" * 60)

    issues_found = 0
    for sg in ec2.security_groups.all():
        for perm in sg.ip_permissions:
            # Check if the port 22 is exposed
            if perm.get("FromPort") == 22 and perm.get("ToPort") == 22:
                for ip_range in perm.get("IpRanges", []):
                    if ip_range.get("CidrIp") == "0.0.0.0/0":
                        print(
                            f"   ❌ RED ALERT : The group '{sg.group_name}' ({sg.id}) opens the SSH to everyone!"
                        )
                        issues_found += 1

    if issues_found == 0:
        print("   ✅ No public SSH access detected. Well done.")
    else:
        print(f"   ⚠️  {issues_found} critical issue(s) detected.")


if __name__ == "__main__":
    print("============================================================")
    print("      AUDIT REPORT INFRASTRUCTURE WEBMARKET+ (FINOPS)    ")
    print("============================================================")

    try:
        total_ec2 = audit_compute()
        total_net = audit_network_cost()
        audit_security_groups()

        total_hourly = total_ec2 + total_net
        total_monthly = total_hourly * 24 * 30

        print("\n💰 FINOPS ESTIMATION")
        print("=" * 60)
        print(f"   Hourly cost estimate: {total_hourly:.4f} $ / hour")
        print(f"   Monthly cost estimate: {total_monthly:.2f} $ / month")
        print("============================================================")

    except ClientError as e:
        print(f"❌ AWS Error: {e}")

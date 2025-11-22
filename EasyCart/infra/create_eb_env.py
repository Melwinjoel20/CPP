import json
import time
from pathlib import Path

import boto3

# ---------- Load config.json ----------
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

with open(CONFIG_PATH, "r") as f:
    cfg = json.load(f)

REGION = cfg["region"]          # "us-east-1"
APP_NAME = "easycart-app-ebs"   # name for EB application
ENV_NAME = "Easycart-app-ebs-env"  # name for EB environment
CNAME_PREFIX = "easycart-dev-env"  # part of public URL, change if conflict


def get_eb():
    return boto3.client("elasticbeanstalk", region_name=REGION)


def ensure_application(eb):
    print(f"Checking if application '{APP_NAME}' exists...")
    resp = eb.describe_applications(ApplicationNames=[APP_NAME])
    if resp.get("Applications"):
        print(f"✅ Application '{APP_NAME}' already exists.")
        return

    print(f"Creating application '{APP_NAME}'...")
    eb.create_application(
        ApplicationName=APP_NAME,
        Description="EasyCart Django app created from Cloud9 script.",
    )
    print("✅ Application created.")


def get_latest_python_platform_arn(eb):
    """
    Find the latest READY Python platform in this region.
    We only filter by PlatformName in the API call, and then
    filter by status='Ready' in Python to avoid older API issues.
    """
    print("Looking up latest READY Python platform...")

    resp = eb.list_platform_versions(
        Filters=[
            {
                "Type": "PlatformName",
                "Operator": "contains",
                "Values": ["Python"],
            }
        ]
    )

    all_platforms = resp.get("PlatformSummaryList", [])
    if not all_platforms:
        raise RuntimeError("No Python platforms found in this region.")

    # Keep only those with status Ready (if field exists)
    ready_platforms = [
        p for p in all_platforms
        if p.get("PlatformStatus") in (None, "Ready")
    ]

    if not ready_platforms:
        raise RuntimeError("No READY Python platforms found in this region.")

    # Pick the newest one by ARN
    ready_platforms.sort(key=lambda p: p["PlatformArn"], reverse=True)
    latest = ready_platforms[0]
    print(f"✅ Using platform: {latest['PlatformArn']}")
    return latest["PlatformArn"]



def ensure_environment(eb):
    print(f"Checking if environment '{ENV_NAME}' exists...")

    # 1️⃣ First check by name (handles reruns)
    resp = eb.describe_environments(
        ApplicationName=APP_NAME,
        EnvironmentNames=[ENV_NAME],
        IncludeDeleted=False,
    )
    envs = [e for e in resp.get("Environments", []) if e["Status"] != "Terminated"]

    if envs:
        env = envs[0]
        env_id = env["EnvironmentId"]
        print(f"✅ Environment '{ENV_NAME}' already exists.")
        print(f"   Current URL: http://{env.get('CNAME')}")
        print(f"   Status: {env['Status']}, Health: {env.get('Health')}")
    else:
        # 2️⃣ If no existing env, create a new one
        platform_arn = get_latest_python_platform_arn(eb)

        print(f"Creating environment '{ENV_NAME}'...")
        resp = eb.create_environment(
            ApplicationName=APP_NAME,
            EnvironmentName=ENV_NAME,
            CNAMEPrefix=CNAME_PREFIX,
            PlatformArn=platform_arn,
            Tier={"Name": "WebServer", "Type": "Standard", "Version": "1.0"},
            OptionSettings=[
                {
                    "Namespace": "aws:elasticbeanstalk:environment",
                    "OptionName": "EnvironmentType",
                    "Value": "SingleInstance",
                },
            ],
        )

        env_id = resp["EnvironmentId"]
        print(f"✅ Environment creation started (ID: {env_id})")

    # 3️⃣ In both cases, wait until it's Ready
    print("Waiting for environment to be Ready... (this can take a while)")

    while True:
        time.sleep(30)

        # 🔁 Always re-query by name, not just by ID
        resp = eb.describe_environments(
            ApplicationName=APP_NAME,
            EnvironmentNames=[ENV_NAME],
            IncludeDeleted=False,
        )
        envs = [e for e in resp.get("Environments", []) if e["Status"] != "Terminated"]

        if not envs:
            print("   Environment not visible yet, still waiting...")
            continue

        env_desc = envs[0]
        status = env_desc["Status"]
        health = env_desc.get("Health")
        cname = env_desc.get("CNAME")

        print(f"   Status: {status}, Health: {health}")

        if status == "Ready":
            print("🎉 Environment is Ready!")
            if cname:
                print(f"   URL: http://{cname}")
            break

        if status in ("Terminating", "Terminated"):
            raise RuntimeError("Environment went into Terminated/Terminating state.")


def main():
    eb = get_eb()
    ensure_application(eb)
    ensure_environment(eb)


if __name__ == "__main__":
    main()

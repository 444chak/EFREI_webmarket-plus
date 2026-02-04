import boto3
import json
import subprocess
import os
import sys


LOCAL_DATA_DIR = os.path.join(
    os.path.dirname(__file__), "../assets"
)  # Folder containing the assets to upload to the datalake
TERRAFORM_DIR = os.path.join(
    os.path.dirname(__file__), "../terraform"
)  # Folder containing the Terraform files


def get_terraform_outputs():
    """Get the outputs of Terraform in JSON format."""
    print(f"🔍 Lecture de la configuration Terraform depuis {TERRAFORM_DIR}...")
    try:
        # Run 'terraform output -json' to get the real values
        cmd = ["terraform", "output", "-json"]
        result = subprocess.run(
            cmd, cwd=TERRAFORM_DIR, capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError:
        print("❌ Erreur : Impossible de lire les outputs Terraform.")
        print("Assure-toi d'avoir fait 'terraform apply' avant.")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Erreur : La commande 'terraform' n'est pas trouvée.")
        sys.exit(1)


def upload_to_s3(bucket_name):
    """Browse the local folder and upload everything to S3."""
    s3 = boto3.client("s3")

    # Check if the local folder exists
    if not os.path.exists(LOCAL_DATA_DIR):
        print(f"❌ Erreur : Le dossier {LOCAL_DATA_DIR} n'existe pas.")
        print("-> Crée un dossier 'data' à la racine et mets-y des images !")
        return

    files = [f for f in os.listdir(LOCAL_DATA_DIR) if not f.startswith(".")]

    if not files:
        print(f"⚠️  Le dossier {LOCAL_DATA_DIR} est vide.")
        return

    print(f"🚀 Début de l'upload vers le bucket : {bucket_name}")
    print(f"📂 Dossier source : {LOCAL_DATA_DIR}")

    for filename in files:
        local_path = os.path.join(LOCAL_DATA_DIR, filename)
        s3_key = (
            f"catalogue/{filename}"  # Properly sort into a 'catalogue' subfolder on S3
        )

        try:
            print(f"   ⬆️  Envoi de {filename}...", end="")
            s3.upload_file(local_path, bucket_name, s3_key)
            print(" OK")
        except Exception as e:
            print(f" ERREUR ({e})")

    print("\n✅ Population du Data Lake terminée avec succès !")


if __name__ == "__main__":
    # Get the name of the bucket created by Terraform
    outputs = get_terraform_outputs()

    # The name of the output must correspond to the outputs.tf file ('s3_bucket_name')
    bucket_name = outputs.get("s3_bucket_name", {}).get("value")

    if not bucket_name:
        print("❌ Erreur : Output 's3_bucket_name' introuvable dans Terraform.")
        sys.exit(1)

    # Run the upload
    upload_to_s3(bucket_name)

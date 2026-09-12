"""One-shot OCI A1 launch; --check performs reads only."""
import argparse
import configparser
import hashlib
import os
from pathlib import Path
import tempfile

import oci

REGION = "mx-queretaro-1"
TENANCY = "ocid1.tenancy.oc1..aaaaaaaahpe236ucfim2ul4qkjhwuvzlwleqnfoyuph776dkegwetbv3oheq"
BOOT = "ocid1.bootvolume.oc1.mx-queretaro-1.abyxeljrxa4tblkmxejfzwkqqfpoas32kbvcj5uu7xj3acrgmbk4zo6bykmq"
SUBNET = "ocid1.subnet.oc1.mx-queretaro-1.aaaaaaaarhz263nmblwfoel4erqdiki5nnvfrkow64yogoqy3fglkcajcokq"
AD = "KsWN:MX-QUERETARO-1-AD-1"


def attempt(compute, block, repository, check=False):
    volume = block.get_boot_volume(BOOT).data
    if volume.availability_domain != AD:
        raise ValueError("Unexpected boot volume availability domain")
    attachments = oci.pagination.list_call_get_all_results(
        compute.list_boot_volume_attachments,
        availability_domain=AD,
        compartment_id=volume.compartment_id,
        boot_volume_id=BOOT,
    ).data
    if any(a.lifecycle_state != "DETACHED" for a in attachments):
        return "attached"
    if volume.lifecycle_state != "AVAILABLE":
        return "unavailable"
    if check:
        return "ready"
    token = hashlib.sha256(f"{repository.lower()}:{BOOT}".encode()).hexdigest()
    details = oci.core.models.LaunchInstanceDetails(
        availability_domain=AD,
        compartment_id=volume.compartment_id,
        display_name="oci-a1-capacity",
        shape="VM.Standard.A1.Flex",
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus=int(os.environ.get("OCI_OCPUS", "2")),
            memory_in_gbs=int(os.environ.get("OCI_MEMORY_GB", "12")),
        ),
        source_details=oci.core.models.InstanceSourceViaBootVolumeDetails(
            boot_volume_id=BOOT,
        ),
        create_vnic_details=oci.core.models.CreateVnicDetails(subnet_id=SUBNET, assign_public_ip=True),
    )
    try:
        compute.launch_instance(
            details, opc_retry_token=token,
            retry_strategy=oci.retry.NoneRetryStrategy(),
        )
    except oci.exceptions.ServiceError as exc:
        # Only the known host-capacity response is a graceful miss, not all 500s.
        if (exc.status == 500 and exc.code == "InternalError"
                and "out of host capacity" in exc.message.lower()):
            return "capacity"
        raise
    return "launched"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        repository = os.environ.get("GITHUB_REPOSITORY") or os.environ["OCI_REPOSITORY"]
        if len(repository.split("/")) != 2 or not all(repository.split("/")):
            raise ValueError("Repository must be owner/name")
        with tempfile.TemporaryDirectory(prefix="oci-a1-") as directory:
            config_path = Path(directory) / "config"
            key_path = Path(directory) / "key.pem"
            for path, secret in ((config_path, "OCI_CONFIG"), (key_path, "OCI_API_KEY")):
                path.touch(mode=0o600)
                path.write_text(os.environ[secret])
            # Replace workstation-specific key paths before SDK path validation.
            parser_config = configparser.ConfigParser(interpolation=None)
            parser_config.read(config_path)
            parser_config["DEFAULT"]["key_file"] = str(key_path)
            with config_path.open("w") as config_file:
                parser_config.write(config_file)
            config = oci.config.from_file(str(config_path), "DEFAULT")
            if config.get("tenancy") != TENANCY:
                raise ValueError("Unexpected tenancy")
            config.update(region=REGION, key_file=str(key_path), log_requests=False)
            oci.config.validate_config(config)
            options = {"retry_strategy": oci.retry.NoneRetryStrategy()}
            result = attempt(oci.core.ComputeClient(config, **options),
                             oci.core.BlockstorageClient(config, **options),
                             repository, args.check)
        print(result)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as output:
                output.write(f"result={result}\n")
        return 0
    except Exception as exc:
        # Never print SDK messages, request bodies, config, or credential material.
        print(f"Failed ({type(exc).__name__}); inspect credentials/configuration or OCI status.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

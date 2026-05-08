"""S3 upload module for MagnitSearch.

Handles uploading generated HTML files to S3-compatible storage
using boto3 with credentials from project AWS config files.
"""

import mimetypes
import os
from configparser import ConfigParser
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError, ProfileNotFound

from config import AWS_CONFIG_PATH, AWS_CREDENTIALS_PATH, AWS_PARAMS_PATH, OUTPUT_DIR


def load_aws_profile(profile_name: str = "default") -> dict:
    """Load AWS profile configuration from the project's AWS config file.

    Reads the AWS config file to get region and endpoint_url for
    the specified profile.

    Args:
        profile_name: Name of the AWS profile to load (default: 'default').

    Returns:
        Dictionary with 'profile_name', 'region', and 'endpoint_url' keys.

    Raises:
        RuntimeError: If the profile is not found in the config file.
    """
    config_parser = ConfigParser()
    config_parser.read(AWS_CONFIG_PATH, encoding="utf-8")

    config_section = (
        profile_name if profile_name == "default" else f"profile {profile_name}"
    )
    if not config_parser.has_section(config_section):
        raise RuntimeError(
            f'AWS profile "{profile_name}" not found in {AWS_CONFIG_PATH}'
        )

    region = config_parser.get(config_section, "region", fallback=None)
    endpoint_url = config_parser.get(config_section, "endpoint_url", fallback=None)
    return {
        "profile_name": profile_name,
        "region": region,
        "endpoint_url": endpoint_url,
    }


def build_s3_client(profile_name: str = "default"):
    """Build an S3 client using the project's AWS configuration.

    Creates a boto3 session and S3 client using the specified profile's
    credentials and configuration.

    Args:
        profile_name: Name of the AWS profile to use (default: 'default').

    Returns:
        Configured boto3 S3 client.

    Raises:
        RuntimeError: If the AWS profile could not be loaded.
    """
    profile = load_aws_profile(profile_name)
    os.environ["AWS_CONFIG_FILE"] = str(AWS_CONFIG_PATH)
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = str(AWS_CREDENTIALS_PATH)

    try:
        session = boto3.session.Session(
            profile_name=profile["profile_name"],
            region_name=profile["region"],
        )
        return session.client(
            "s3",
            endpoint_url=profile["endpoint_url"],
        )
    except ProfileNotFound as exc:
        raise RuntimeError(
            f'AWS profile "{profile_name}" could not be loaded from project .aws files'
        ) from exc


def load_upload_params() -> dict:
    """Load S3 upload parameters from the project's params file.

    Reads bucket_name and prefix from the AWS params configuration file.

    Returns:
        Dictionary with 'bucket_name' and 'prefix' keys.
    """
    params_parser = ConfigParser()
    params_parser.read(AWS_PARAMS_PATH, encoding="utf-8")
    if not params_parser.has_section("default"):
        return {"bucket_name": "", "prefix": ""}

    return {
        "bucket_name": params_parser.get("default", "bucket_name", fallback=""),
        "prefix": params_parser.get("default", "prefix", fallback=""),
    }


def save_upload_params(bucket_name: str, prefix: str) -> None:
    """Save S3 upload parameters to the project's params file.

    Stores the bucket name and key prefix to the AWS params file
    for future use.

    Args:
        bucket_name: S3 bucket name.
        prefix: Key prefix for uploaded objects.
    """
    params_parser = ConfigParser()
    params_parser["default"] = {
        "bucket_name": bucket_name,
        "prefix": prefix,
    }
    AWS_PARAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AWS_PARAMS_PATH.open("w", encoding="utf-8") as params_file:
        params_parser.write(params_file)


def prompt_bucket_name(default_bucket_name: str = "") -> str:
    """Prompt the user to enter an S3 bucket name.

    Displays a prompt with the default value (if any) and returns
    the user's input or the default.

    Args:
        default_bucket_name: Default bucket name to show in prompt.

    Returns:
        Entered or default bucket name.

    Raises:
        ValueError: If no bucket name is provided.
    """
    prompt = "Enter S3 bucket name"
    if default_bucket_name:
        prompt += f" [{default_bucket_name}]"
    prompt += ": "

    bucket_name = input(prompt).strip()
    if not bucket_name:
        bucket_name = default_bucket_name
    if not bucket_name:
        raise ValueError("Bucket name is required")
    return bucket_name


def prompt_key_prefix(default_prefix: str = "") -> str:
    """Prompt the user to enter an S3 key prefix.

    Asks for a key prefix (path prefix) for uploaded objects.
    The prefix is stripped of leading/trailing slashes.

    Args:
        default_prefix: Default prefix to show in prompt.

    Returns:
        Entered or default prefix string.
    """
    prompt = "Enter key prefix, or leave empty for bucket root"
    if default_prefix:
        prompt += f" [{default_prefix}]"
    prompt += ": "

    prefix = input(prompt).strip()
    if not prefix:
        prefix = default_prefix
    prefix = prefix.strip("/")
    return prefix


def iter_output_files() -> list[Path]:
    """Get a sorted list of all files in the output directory.

    Returns a sorted list of all files (recursively) in the output
    directory.

    Returns:
        Sorted list of Path objects for each file.

    Raises:
        RuntimeError: If output directory doesn't exist or is empty.
    """
    if not OUTPUT_DIR.exists():
        raise RuntimeError(f"Output directory not found: {OUTPUT_DIR}")

    files = sorted(path for path in OUTPUT_DIR.rglob("*") if path.is_file())
    if not files:
        raise RuntimeError(f"No files found in output directory: {OUTPUT_DIR}")
    return files


def build_object_key(file_path: Path, prefix: str) -> str:
    """Build an S3 object key from a file path and prefix.

    Converts the file path to a relative path from the output directory
    and prepends the prefix if provided.

    Args:
        file_path: Path to the local file.
        prefix: S3 key prefix (without leading/trailing slashes).

    Returns:
        Full S3 object key string.
    """
    relative_path = file_path.relative_to(OUTPUT_DIR).as_posix()
    if not prefix:
        return relative_path
    return f"{prefix}/{relative_path}"


def upload_output_to_s3(
    bucket_name: str, prefix: str = "", profile_name: str = "default"
) -> int:
    """Upload all files from the output directory to S3.

    Iterates through all files in the output directory and uploads
    them to the specified S3 bucket with appropriate content types.

    Args:
        bucket_name: Target S3 bucket name.
        prefix: Key prefix for uploaded objects.
        profile_name: AWS profile to use for credentials.

    Returns:
        Number of files successfully uploaded.

    Raises:
        RuntimeError: If any upload fails.
    """
    s3_client = build_s3_client(profile_name)
    files = iter_output_files()

    uploaded_count = 0
    for file_path in files:
        object_key = build_object_key(file_path, prefix)
        content_type, _ = mimetypes.guess_type(file_path.name)
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            if extra_args:
                s3_client.upload_file(
                    str(file_path),
                    bucket_name,
                    object_key,
                    ExtraArgs=extra_args,
                )
            else:
                s3_client.upload_file(str(file_path), bucket_name, object_key)
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"Failed to upload {file_path.name}: {exc}") from exc

        uploaded_count += 1
        print(f"Uploaded {file_path.name} -> s3://{bucket_name}/{object_key}")

    return uploaded_count


def run_upload_mode() -> None:
    """Run the S3 upload mode.

    Loads saved upload parameters, prompts for bucket name and prefix,
    saves the parameters for future use, and uploads all output files to S3.
    """
    saved_params = load_upload_params()
    bucket_name = prompt_bucket_name(saved_params["bucket_name"])
    prefix = prompt_key_prefix(saved_params["prefix"])
    save_upload_params(bucket_name, prefix)
    uploaded_count = upload_output_to_s3(bucket_name, prefix=prefix)
    print(f"Uploaded {uploaded_count} files from {OUTPUT_DIR}")

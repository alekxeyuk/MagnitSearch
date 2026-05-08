import mimetypes
import os
from configparser import ConfigParser
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError, ProfileNotFound

PROJECT_ROOT = Path(__file__).resolve().parent
AWS_CONFIG_PATH = PROJECT_ROOT / '.aws' / 'config'
AWS_CREDENTIALS_PATH = PROJECT_ROOT / '.aws' / 'credentials'
AWS_PARAMS_PATH = PROJECT_ROOT / '.aws' / 'params'
OUTPUT_DIR = PROJECT_ROOT / 'output'


def load_aws_profile(profile_name: str = 'default') -> dict:
    config_parser = ConfigParser()
    config_parser.read(AWS_CONFIG_PATH, encoding='utf-8')

    config_section = profile_name if profile_name == 'default' else f'profile {profile_name}'
    if not config_parser.has_section(config_section):
        raise RuntimeError(f'AWS profile "{profile_name}" not found in {AWS_CONFIG_PATH}')

    region = config_parser.get(config_section, 'region', fallback=None)
    endpoint_url = config_parser.get(config_section, 'endpoint_url', fallback=None)
    return {
        'profile_name': profile_name,
        'region': region,
        'endpoint_url': endpoint_url,
    }


def build_s3_client(profile_name: str = 'default'):
    profile = load_aws_profile(profile_name)
    os.environ['AWS_CONFIG_FILE'] = str(AWS_CONFIG_PATH)
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = str(AWS_CREDENTIALS_PATH)

    try:
        session = boto3.session.Session(
            profile_name=profile['profile_name'],
            region_name=profile['region'],
        )
        return session.client(
            's3',
            endpoint_url=profile['endpoint_url'],
        )
    except ProfileNotFound as exc:
        raise RuntimeError(
            f'AWS profile "{profile_name}" could not be loaded from project .aws files'
        ) from exc


def load_upload_params() -> dict:
    params_parser = ConfigParser()
    params_parser.read(AWS_PARAMS_PATH, encoding='utf-8')
    if not params_parser.has_section('default'):
        return {'bucket_name': '', 'prefix': ''}

    return {
        'bucket_name': params_parser.get('default', 'bucket_name', fallback=''),
        'prefix': params_parser.get('default', 'prefix', fallback=''),
    }


def save_upload_params(bucket_name: str, prefix: str) -> None:
    params_parser = ConfigParser()
    params_parser['default'] = {
        'bucket_name': bucket_name,
        'prefix': prefix,
    }
    AWS_PARAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AWS_PARAMS_PATH.open('w', encoding='utf-8') as params_file:
        params_parser.write(params_file)


def prompt_bucket_name(default_bucket_name: str = '') -> str:
    prompt = 'Enter S3 bucket name'
    if default_bucket_name:
        prompt += f' [{default_bucket_name}]'
    prompt += ': '

    bucket_name = input(prompt).strip()
    if not bucket_name:
        bucket_name = default_bucket_name
    if not bucket_name:
        raise ValueError('Bucket name is required')
    return bucket_name


def prompt_key_prefix(default_prefix: str = '') -> str:
    prompt = 'Enter key prefix, or leave empty for bucket root'
    if default_prefix:
        prompt += f' [{default_prefix}]'
    prompt += ': '

    prefix = input(prompt).strip()
    if not prefix:
        prefix = default_prefix
    prefix = prefix.strip('/')
    return prefix


def iter_output_files() -> list[Path]:
    if not OUTPUT_DIR.exists():
        raise RuntimeError(f'Output directory not found: {OUTPUT_DIR}')

    files = sorted(path for path in OUTPUT_DIR.rglob('*') if path.is_file())
    if not files:
        raise RuntimeError(f'No files found in output directory: {OUTPUT_DIR}')
    return files


def build_object_key(file_path: Path, prefix: str) -> str:
    relative_path = file_path.relative_to(OUTPUT_DIR).as_posix()
    if not prefix:
        return relative_path
    return f'{prefix}/{relative_path}'


def upload_output_to_s3(bucket_name: str, prefix: str = '', profile_name: str = 'default') -> int:
    s3_client = build_s3_client(profile_name)
    files = iter_output_files()

    uploaded_count = 0
    for file_path in files:
        object_key = build_object_key(file_path, prefix)
        content_type, _ = mimetypes.guess_type(file_path.name)
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type

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
            raise RuntimeError(f'Failed to upload {file_path.name}: {exc}') from exc

        uploaded_count += 1
        print(f'Uploaded {file_path.name} -> s3://{bucket_name}/{object_key}')

    return uploaded_count


def run_upload_mode() -> None:
    saved_params = load_upload_params()
    bucket_name = prompt_bucket_name(saved_params['bucket_name'])
    prefix = prompt_key_prefix(saved_params['prefix'])
    save_upload_params(bucket_name, prefix)
    uploaded_count = upload_output_to_s3(bucket_name, prefix=prefix)
    print(f'Uploaded {uploaded_count} files from {OUTPUT_DIR}')

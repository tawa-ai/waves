import asyncio
import os
from typing import Optional, Tuple

TF_PLAN_FILE = "plan.tfplan"


async def apply_changes(tf_file_path: str) -> Tuple[bytes, bytes]:
    """Apply the changes through async sub process

    Args:
        tf_file_path (str): Path to the tf file.

    Returns:
        Tuple[bytes, bytes]: Stdout and stderr from async subproc run.
    """
    full_command = f"cd {os.path.dirname(tf_file_path)} && terraform apply"

    full_command += f" {TF_PLAN_FILE}"

    tf_apply_proc = await asyncio.create_subprocess_shell(
        full_command, stderr=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
    )
    stdout, stderr = await tf_apply_proc.communicate()
    return stdout, stderr


async def plan_changes(tf_file_path: str, target_resource_name: Optional[str] = None) -> Tuple[bytes, bytes]:
    """Plan the changes through async sub process.

    Args:
        tf_file_path (str): Path to the tf file.
        target_resource_name (Optional[str], optional): Optional switch to only tf plan to certain resource. Defaults to None.

    Returns:
        Tuple[bytes, bytes]: Stdout and stderr from async subproc run.
    """
    full_command = f"cd {os.path.dirname(tf_file_path)} && terraform plan -out=module.{TF_PLAN_FILE}"

    if target_resource_name:
        full_command += f" -target={target_resource_name}"

    tf_plan_proc = await asyncio.create_subprocess_shell(
        full_command, stderr=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
    )
    stdout, stderr = await tf_plan_proc.communicate()
    return stdout, stderr


async def init_terraform(tf_file_path: str) -> Tuple[bytes, bytes]:
    """Init terraform in tf file repo.

    Args:
        tf_file_path (str): Path to the tf file.

    Returns:
        Tuple[bytes, bytes]: Stdout and stderr from async subproc run.
    """
    full_command = f"cd {os.path.dirname(tf_file_path)} && terraform init"
    tf_init_proc = await asyncio.create_subprocess_shell(
        full_command, stderr=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
    )
    stdout, stderr = await tf_init_proc.communicate()
    return stdout, stderr

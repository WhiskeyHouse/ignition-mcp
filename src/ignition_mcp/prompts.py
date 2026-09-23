"""Runbook prompts: the exact tools to call, in order, and the composite shortcut."""

from __future__ import annotations

from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt
    def health_check() -> str:
        """Daily gateway health check runbook."""
        return (
            "Check the active Ignition gateway's health.\n"
            "1. Call status. If ok is false, stop and report the error code and hint.\n"
            "2. Call license_status, redundancy_status, gan_status, connections, modules, doctor.\n"
            "3. Report: version, uptime, license mode, any module whose state is not ACTIVE "
            "or RUNNING, any database connection with enabled: false, any doctor check whose "
            "status is Fail.\n"
            "Shortcut: diagnose_gateway does steps 1 to 3 in one call and returns a verdict."
        )

    @mcp.prompt
    def bring_up_rig() -> str:
        """Bring a Docker test rig to a fresh, reachable gateway."""
        return (
            "Bring up a fresh test rig.\n"
            "1. Call rig_status to see what is running.\n"
            "2. If containers exist and a clean slate is wanted, call rig_down with "
            "confirm: true.\n"
            "3. Call rig_up, then wait_gateway, then status.\n"
            "Shortcut: rig_fresh with confirm: true does steps 2 and 3."
        )

    @mcp.prompt
    def sync_project(project: str, profile_a: str, profile_b: str) -> str:
        """Promote a project from one gateway profile to another safely."""
        return (
            f"Promote project {project} from profile {profile_a} to profile {profile_b}.\n"
            f"1. Call project_diff with profile_a: {profile_a}, profile_b: {profile_b}, "
            f"project: {project}. If the summary is all zeros, stop and say there is nothing "
            "to promote.\n"
            f"2. Call project_sync with profile_a: {profile_a}, profile_b: {profile_b}, "
            f"project: {project}, all-changed: true, confirm: true.\n"
            "3. Call project_diff again with the same three arguments to verify the profiles "
            "now match.\n"
            f"Shortcut: deploy_project({project}, {profile_a}, {profile_b}, confirm: true) does "
            "all three and refuses with nothing_to_promote when the profiles are already "
            "identical."
        )

    @mcp.prompt
    def push_local_edits(path: str) -> str:
        """Push local workspace edits to the gateway safely."""
        return (
            f"Push the local edits in the workspace at {path} to its gateway project.\n"
            f"1. Call workspace_status with path: {path}. If clean is true, stop and say there "
            "is nothing to push.\n"
            "2. Review the rows. If any row's kind is conflict, stop: conflicts cannot be "
            "pushed even with confirm. Reconcile locally and re-run `ign workspace checkout` "
            "for this project; a conflict right after a successful push only needs the "
            "re-checkout. Report each "
            "local_edit, added, and deleted row; deletions are pushed only with delete: true.\n"
            f"3. Call workspace_push with path: {path}, confirm: true.\n"
            f"4. Call workspace_status with path: {path} again. Every member workspace_push "
            "wrote must no longer be local_edit. ign does not advance the workspace baseline "
            "on push, so pushed members now read as conflict; that is expected.\n"
            "5. Re-run `ign workspace checkout` for this project before pushing again, so the "
            "baseline matches the gateway.\n"
            f"Shortcut: push_workspace({path}, confirm: true) does steps 1 to 4, refuses with "
            "workspace_conflict or nothing_to_push before pushing anything, and still needs "
            "step 5 afterwards."
        )

    @mcp.prompt
    def triage_alarm(path: str) -> str:
        """Investigate an active alarm on a tag path."""
        return (
            f"Triage the alarm on {path}.\n"
            f"1. Call tags_alarms_active and find entries whose source contains {path}.\n"
            f"2. Call tags_read with paths=[{path}] for the current value and quality.\n"
            f"3. Call tags_alarms_history for {path} to see how often it fires.\n"
            "4. Summarize: priority, current value, first and last occurrence, likely cause.\n"
            "Do not acknowledge (tags_alarms_ack) unless asked."
        )

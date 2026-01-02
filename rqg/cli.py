import sys
import click
from pathlib import Path
from rqg.collect import collect_artifacts
from rqg.analyze import analyze_run
from rqg.explain import explain_test
from rqg.upload import upload_bundle


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Release Quality Gate - CI test analysis and gating system"""
    pass


@main.command()
@click.option("--config", "-c", default="rqg.yml", help="Config file path")
@click.option("--output", "-o", default="rqg/bundle.jsonl", help="Output bundle path")
@click.option("--repo", help="Repository name (auto-detected if not provided)")
@click.option("--branch", help="Branch name (auto-detected if not provided)")
@click.option("--commit", help="Commit SHA (auto-detected if not provided)")
@click.option("--workflow", help="CI workflow/job name")
@click.option("--build-number", help="CI build number")
@click.option("--attempt", type=int, help="Retry attempt number")
def collect(config, output, repo, branch, commit, workflow, build_number, attempt):
    """Collect artifacts from workspace and create bundle"""
    try:
        bundle_path = collect_artifacts(
            config_path=config,
            output_path=output,
            repo=repo,
            branch=branch,
            commit=commit,
            workflow=workflow,
            build_number=build_number,
            attempt=attempt,
        )
        click.echo(f"Bundle created: {bundle_path}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--config", "-c", default="rqg.yml", help="Config file path")
@click.option("--bundle", "-b", default="rqg/bundle.jsonl", help="Bundle file path")
@click.option("--output-dir", "-o", default="rqg", help="Output directory for decision files")
def analyze(config, bundle, output_dir):
    """Analyze current run with history and produce decision"""
    try:
        decision = analyze_run(
            config_path=config,
            bundle_path=bundle,
            output_dir=output_dir,
        )
        exit_code = {
            "PASS": 0,
            "SOFT_BLOCK": 10,
            "HARD_BLOCK": 20,
        }.get(decision.get("decision"), 1)
        sys.exit(exit_code)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("test_id")
@click.option("--config", "-c", default="rqg.yml", help="Config file path")
@click.option("--history-dir", default=".rqg", help="History database directory")
def explain(test_id, config, history_dir):
    """Explain a test or failure cluster with evidence"""
    try:
        explain_test(test_id, config_path=config, history_dir=history_dir)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--bundle", "-b", default="rqg/bundle.jsonl", help="Bundle file path")
@click.option("--api-url", help="RQG API URL")
@click.option("--token", help="API token")
def upload(bundle, api_url, token):
    """Upload bundle to central RQG service"""
    try:
        upload_bundle(bundle_path=bundle, api_url=api_url, token=token)
        click.echo("Bundle uploaded successfully")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

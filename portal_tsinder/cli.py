"""Command line, offline reproducibility and single-process service startup."""
import argparse
import json
from pathlib import Path
import sys
from .contracts import strict_json
from .service import KINDS, run_experiment, catalog
from .storage import Store, verify_bundle
from .locking import ServiceLock
from .reports import render


def output(value, path=None):
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n"
    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def main(argv=None):
    parser = argparse.ArgumentParser(description="PORTAL TSINDER research workbench; no physical actuator")
    parser.add_argument("--data-dir", default=".portal")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="initialize database and local API token")
    sub.add_parser("token", help="display the local API token on YOUR terminal")
    serve = sub.add_parser("serve")
    serve.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    run = sub.add_parser("run")
    run.add_argument("kind", choices=KINDS)
    run.add_argument("--config", type=Path)
    run.add_argument("--output", type=Path)
    demo = sub.add_parser("demo")
    demo.add_argument("--output", type=Path)
    sub.add_parser("list")
    show = sub.add_parser("show")
    show.add_argument("id")
    for name in ("export", "report"):
        p = sub.add_parser(name)
        p.add_argument("id")
        p.add_argument("output", type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("--expected-head")
    vb = sub.add_parser("verify-bundle")
    vb.add_argument("path", type=Path)
    cat = sub.add_parser("catalog")
    cat.add_argument("name", choices=["models", "layers", "capabilities", "candidate.schema"])
    reset = sub.add_parser("reset-lockout")
    reset.add_argument("--reviewer", required=True)
    reset.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    try:
        directory = Path(args.data_dir)
        if args.command == "catalog":
            output(catalog(args.name))
            return 0
        if args.command == "verify-bundle":
            valid = verify_bundle(args.path.read_bytes())
            output({"status": "PASS" if valid else "FAIL"})
            return 0 if valid else 1
        if args.command in ("init", "token", "serve"):
            from .api import initialize_data, create_app
            directory, token = initialize_data(directory)
            if args.command == "token":
                print(token)
                return 0
            if args.command == "serve":
                import uvicorn
                print(f"Research workbench: http://127.0.0.1:{args.port}")
                print("Read the local token with: python -m portal_tsinder --data-dir PATH token")
                uvicorn.run(create_app(directory), host=args.host, port=args.port, workers=1,
                            log_level="info", limit_concurrency=32, timeout_keep_alive=5)
                return 0
        store = Store(directory/"portal.sqlite")
        if args.command == "init":
            output({"status": "initialized", "token_file": str(directory/"operator.token"),
                    "mode": "RESEARCH_SIMULATION_ONLY"})
        elif args.command == "run":
            parameters = strict_json(args.config.read_text()) if args.config else {}
            output(run_experiment(store, args.kind, parameters), args.output)
        elif args.command == "demo":
            configs = [("evaluate", {}), ("geodesic", {}), ("wave", {}),
                       ("quantum", {}), ("control", {}), ("wave_convergence", {})]
            results = []
            for kind, config in configs:
                run = run_experiment(store, kind, config)
                results.append({"id": run["id"], "kind": kind, "result_sha": run["result_sha"]})
            output({"runs": results, "audit": store.verify()}, args.output)
        elif args.command == "list":
            output(store.runs())
        elif args.command == "show":
            output(store.get_run(args.id))
        elif args.command == "export":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(store.export(args.id))
            print(args.output)
        elif args.command == "report":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(render(store.get_run(args.id)), encoding="utf-8")
            print(args.output)
        elif args.command == "verify":
            result = store.verify(args.expected_head)
            output(result)
            return 0 if result["status"] == "PASS" else 1
        elif args.command == "reset-lockout":
            if not args.reviewer.strip() or len(args.reason.strip()) < 10:
                raise ValueError("reviewer and meaningful review reason required")
            with ServiceLock(directory/"service.lock"):
                if store.verify()["status"] != "PASS":
                    raise ValueError("cannot reset with a broken provenance chain")
                store.event("OFFLINE_REVIEW", {"reviewer": args.reviewer, "reason": args.reason,
                                               "identity_assurance": "SELF_ATTESTED_LOCAL_OPERATOR"})
                store.set_state("lockout", False, "OFFLINE_LOCKOUT_RESET")
                store.set_state("service_dirty", False, "OFFLINE_SHUTDOWN_REVIEW")
                output({"state": "OFF", "review_logged": True, "physical_output": False})
        return 0
    except (ValueError, KeyError, RuntimeError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

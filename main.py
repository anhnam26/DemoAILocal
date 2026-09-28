"""Run the complete web application with the active Python/Conda environment."""
import argparse
import os
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def port_number(value):
    try:
        port = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError('Port must be an integer from 1 to 65535.')
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError('Port must be an integer from 1 to 65535.')
    return port


def main(argv=None):
    # Resolve relative APP_DATA_DIR consistently even when launched from elsewhere.
    os.chdir(ROOT)
    import config

    values = config.env()
    parser = argparse.ArgumentParser(description='CyberAnt web UI and OpenRouter API server')
    parser.add_argument('--host', default=values.get('APP_HOST', '127.0.0.1'))
    parser.add_argument('--port', type=port_number, default=values.get('APP_PORT', '8088'))
    args = parser.parse_args(argv)
    try:
        config.security()
        import uvicorn
    except ImportError as exc:
        parser.exit(1, f'Missing dependency: {exc.name}. Run: python -m pip install -r requirements-lock.txt\n')
    except ValueError as exc:
        parser.exit(1, f'Invalid application configuration: {exc}\n')

    settings = uvicorn.Config(
        'app:app', host=args.host, port=args.port, workers=1,
        proxy_headers=False, timeout_graceful_shutdown=400,
    )
    # Bind before importing app: a duplicate start must not run DB crash recovery.
    try:
        listener = socket.create_server(
            (args.host, args.port),
            family=socket.AF_INET6 if ':' in args.host else socket.AF_INET,
            backlog=settings.backlog,
        )
    except OSError as exc:
        parser.exit(1, f'Cannot listen on {args.host}:{args.port}: {exc}\n')
    try:
        print(f'Starting CyberAnt at http://{args.host}:{args.port}', flush=True)
        server = uvicorn.Server(settings)
        server.run(sockets=[listener])
        if not server.started:
            raise SystemExit(1)
    finally:
        listener.close()


if __name__ == '__main__':
    main()

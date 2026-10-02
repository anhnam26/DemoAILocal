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
    from cyberant import config

    values = config.env()
    parser = argparse.ArgumentParser(description='CyberAnt web UI and OpenRouter API server')
    parser.add_argument('--host', default=values.get('APP_HOST', '127.0.0.1'))
    parser.add_argument('--port', type=port_number, default=values.get('APP_PORT', '8088'))
    parser.add_argument('--share', action='store_true', help='Linux: temporary public HTTPS URL; existing private DB required')
    parser.add_argument('--cloudflared', default='cloudflared', help='Path to the installed cloudflared executable')
    parser.add_argument('--share-protocol', choices=('auto', 'http2', 'quic'), default='auto')
    args = parser.parse_args(argv)
    binary = None
    try:
        if args.share:
            from cyberant import public_share
            binary = public_share.preflight(ROOT, config.data_dir(), args.cloudflared)
            args.host = '127.0.0.1'
            os.umask(0o077)
        else:
            security=config.security()
            if security['mode']=='development' and args.host not in ('127.0.0.1','localhost','::1'):
                raise ValueError('Development must bind loopback; configure lan/production for network access')
        # Validate dependencies/config before opening a listener.
        import importlib
        for dependency in ('uvicorn','fastapi','httpx','numpy','sklearn','pypdf','python_multipart'):
            importlib.import_module(dependency)
        from cyberant import model_provider
        import uvicorn
        model_provider.settings()
        if not args.share and security['mode']=='lan':print('LAN HTTP: traffic is not encrypted. Restrict access with the server firewall.',flush=True)
    except ImportError as exc:
        parser.exit(1, f'Missing dependency: {exc.name}. Run: python -m pip install -r requirements-lock.txt\n')
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Invalid application configuration: {exc}\n')

    settings = uvicorn.Config(
        'cyberant.app:app', host=args.host, port=args.port, workers=1,
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
    instance = None
    try:
        from cyberant import runtime_lock,storage
        instance = runtime_lock.acquire(config.data_dir())
        storage.validate(config.data_dir(),integrity=True)
        server = uvicorn.Server(settings)
        if args.share:
            public_share.validate_database(config.data_dir())
            public_share.serve(server, listener, binary, args.port, args.share_protocol)
        else:
            print(f'Starting CyberAnt at http://{args.host}:{args.port}', flush=True)
            server.run(sockets=[listener])
        if not server.started:
            raise SystemExit(1)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(1, f'Cannot start CyberAnt: {exc}\n')
    finally:
        listener.close()
        if instance is not None:
            instance.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        # Uvicorn re-raises SIGINT after finishing its graceful shutdown.
        print('\nCyberAnt stopped.')

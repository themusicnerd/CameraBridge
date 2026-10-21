# Security

## Accounts and sessions

Create accounts through the local interactive command.
Use `--init-user NAME --role admin` or `--role operator`.
The command replaces an existing account with the same name.
It stores a salted PBKDF2-SHA256 password hash in SQLite.
The hash uses 250000 iterations.
Passwords must be non-empty. This release has no minimum password length.

Sessions expire after eight hours.
They exist only in service memory.
Restart ends all sessions.
Changing an account does not end existing session tokens immediately.
Stop the service if immediate session removal is required.

The native password field clears after sign-in.
Keep passwords out of saved grid files, configuration, logs and repositories.
The browser and panels require separate sign-in.
The Open CameraBridge button does not transfer a token.

## Network access

The default HTTP address is loopback.
Trusted CIDR entries restrict HTTP clients.
Write requests require authentication and the applicable role.
Cookies are not used for authentication.
Cross-origin browser writes are rejected.

The TouchDrive host accepts its configured panel address and the host address only.
It forwards configuration requests with the original login token.
Only backend administrators can read or save configuration.
The host does not expose service shutdown or arbitrary files.

The lab VISCA protocol has no login field.
The loopback listener permits Panasonic emulator targets only.
The optional LAN relay permits one configured Carbonite address.
It checks lab mode and the emulator target before a connection.
Store commands also require `--visca-allow-store`.

## Limits

Use a trusted management network.
The development panel host uses plain HTTP.
Use a suitable HTTPS reverse proxy for remote production administration.
The backend does not trust forwarded address headers.
Its standard-library HTTP server is not hardened for internet exposure.

The service limits body size, request threads and socket wait time.
Eight failed login attempts per client within one minute cause a temporary block.
No request body, password, authorization header or session token is logged.
Diagnostic exports omit the credential database.
Review diagnostics before sharing them; they contain host and camera information.

Restrict access to the data directory and backups.
Physical camera authentication is not implemented.
Do not put camera passwords in host URLs.

Configured PIVOTCam endpoints accept only the specified controller IP.
VISCA does not provide authentication or encryption.
Restrict these TCP ports to the isolated camera-control network.

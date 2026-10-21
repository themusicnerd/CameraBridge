# Security

All write/control APIs require an authenticated session. Users are provisioned interactively by CLI; passwords are salted PBKDF2-SHA256 hashes in SQLite (250,000 iterations), not cleartext source/configuration. Sessions expire after eight hours, live only in memory and are invalidated at process exit. Native panels and web UI keep tokens in memory. Native password fields clear on sign-in.

Operator/admin roles are enforced for configuration and lockout. Trusted management CIDRs are checked before API dispatch. Cookies are not used; bearer tokens or explicitly supplied ogScript session tokens are required. Cross-origin requests are rejected. Browser login tokens are not stored in localStorage. Responses are no-store and anti-framing headers are set. Login attempts are rate limited per client address. HTTP requests have bounded body size, socket timeouts and a 24-thread limit.

LAB allows unauthenticated **read-only state** only from loopback. Every REST/ogScript control still requires login. CGI simulators are intentionally unauthenticated loopback-only services and contain no real credentials. Lab mode refuses non-loopback binding and non-simulated cameras.

The explicitly enabled lab serial-VISCA/TCP listeners implement a protocol with no user-login field. They are isolated loopback test ingress, accept simulated Panasonic targets only and are never exposed as the authenticated REST API. Remote preset stores require an additional startup flag. Simulator bus-selection and service-stop API endpoints still require an administrator session. A future hardware listener needs separately reviewed management-host restrictions and protocol acceptance; it is not enabled here.

No request bodies, Authorization headers or camera credentials are logged. Diagnostic events contain parameter IDs/values and generic exception class names. The diagnostics download omits the user database and sessions. Process discovery records executable names rather than full arguments. Configuration currently has no camera credential fields or authenticated-camera support; do not put passwords into host URLs.

Limitations requiring hardening before production: TLS is supplied by a reverse proxy, no automated account-revocation UI, no exhaustive denial-of-service testing, configuration schema is preliminary, and stdlib HTTP is not intended as a public server. Configure trusted proxy/host rules carefully; forwarded headers are not trusted by this backend. Restrict runtime-directory permissions on Linux and Windows. Do not expose management services to the internet.

Do not save native .grid files with typed passwords. Obtain unknown credentials interactively from the equipment owner; no password guessing or embedding vendor credentials is part of this project.

# Security and safety

Report code-execution or privilege-escalation issues privately through GitHub's
security-advisory flow.

This toolkit runs as root and touches cooling control and Proxmox-owned files.
Review every script and configuration before deployment. Do not paste private
SSH keys, public-network host addresses, cluster credentials, or production
configuration dumps into an issue.

Fan-control configuration is parsed as declarative data; arbitrary keys,
commands, traversal paths, and non-sysfs targets are rejected. Keep the config
root-owned and non-writable by unprivileged users. Deployment rejects SSH hosts
that could be interpreted as command-line options.

For a suspected thermal-control failure, stop the service, restore full/manual
fan speed through firmware or sysfs, and verify temperatures locally before
debugging the automation.
